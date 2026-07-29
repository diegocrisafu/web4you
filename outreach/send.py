#!/usr/bin/env python3
"""
web4you outreach sender.

Dry run is the default. Nothing leaves your machine unless you pass --send.

    python send.py                          # preview every pending message
    python send.py --limit 5                # preview the first 5
    python send.py --send --limit 5         # actually send 5
    python send.py --unsubscribe a@b.com    # add an address to the suppression list

Setup:
    cp .env.example .env      # then fill it in
    pip install python-dotenv

CASL (Canada's Anti-Spam Legislation) applies to you. Read README.md before
sending anything. This script enforces the mechanical parts -- identification,
mailing address, unsubscribe -- but it cannot establish consent for you.
"""

import argparse
import csv
import os
import random
import smtplib
import ssl
import sys
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

HERE = Path(__file__).parent
PROSPECTS = HERE / "prospects.csv"
SUPPRESSION = HERE / "suppression.txt"
SENT_LOG = HERE / "sent_log.csv"

# Loaded from .env
CFG = {}


# ----------------------------------------------------------------- config

def load_config():
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            CFG[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        if k.startswith(("SMTP_", "SENDER_", "REPLY_", "REQUIRE_", "DEFAULT_")):
            CFG[k] = v

    required = [
        "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS",
        "SENDER_NAME", "SENDER_EMAIL", "SENDER_ADDRESS",
    ]
    missing = [k for k in required if not CFG.get(k)]
    if missing:
        sys.exit(
            "Missing config: " + ", ".join(missing) +
            "\nCopy .env.example to .env and fill it in."
        )
    # Every string .env.example ships with, so an unedited copy can never send.
    # A placeholder mailing address in a commercial message is a CASL violation
    # on its own, regardless of who you sent it to.
    PLACEHOLDERS = (
        "example.com", "yourdomain", "you@gmail.com",
        "your street address", "postal", "your_16_char",
    )
    for key in ("SENDER_EMAIL", "SENDER_ADDRESS", "SMTP_PASS"):
        lowered = CFG[key].lower()
        hit = next((p for p in PLACEHOLDERS if p in lowered), None)
        if hit:
            sys.exit(
                f"{key} still holds placeholder text from .env.example ({hit!r}).\n"
                "CASL requires your real name and a real mailing address in every "
                "message. Edit .env before sending."
            )


# ----------------------------------------------------- suppression + log

def load_suppression():
    out = set()
    if SUPPRESSION.exists():
        for line in SUPPRESSION.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip().lower()
            if line:
                out.add(line)
    return out


def add_suppression(addr):
    addr = addr.strip().lower()
    current = load_suppression()
    if addr in current:
        print(f"{addr} was already suppressed.")
        return
    with SUPPRESSION.open("a", encoding="utf-8") as f:
        f.write(f"{addr}  # added {datetime.now(timezone.utc):%Y-%m-%d}\n")
    print(f"Suppressed {addr}. It will never be contacted again by this script.")


def load_already_sent():
    out = set()
    if SENT_LOG.exists():
        with SENT_LOG.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("email"):
                    out.add(row["email"].strip().lower())
    return out


def log_sent(row, subject, message_id):
    new = not SENT_LOG.exists()
    with SENT_LOG.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["sent_at_utc", "business", "email", "subject", "message_id"])
        w.writerow([
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            row.get("business", ""), row.get("email", ""), subject, message_id,
        ])


# --------------------------------------------------------------- rendering

def render(text, row):
    """Replace {field} with the row's value. Unknown fields raise rather than
    silently shipping a literal '{first_name}' to a prospect."""
    out = text
    for key, val in row.items():
        out = out.replace("{" + key + "}", (val or "").strip())
    leftover = [
        seg.split("}")[0]
        for seg in out.split("{")[1:]
        if "}" in seg
    ]
    if leftover:
        raise ValueError(
            f"Unfilled merge fields {sorted(set(leftover))} for "
            f"{row.get('business', '?')}. Fill those CSV columns or edit the template."
        )
    return out


FOOTERS = {
    "fr": (
        "\n\n—\n{sender_name}\n{sender_email}\n{sender_address}\n\n"
        "Vous recevez ce message parce que votre adresse est publiée publiquement "
        "pour votre entreprise. Pour ne plus jamais être contacté, répondez avec "
        "le mot RETRAIT et je vous retirerai de ma liste."
    ),
    "en": (
        "\n\n—\n{sender_name}\n{sender_email}\n{sender_address}\n\n"
        "You're receiving this because your address is publicly listed for your "
        "business. To never be contacted again, reply with the word UNSUBSCRIBE "
        "and I'll remove you."
    ),
}


def build_message(row, template_text, subject_line):
    lang = (row.get("lang") or "fr").lower()
    if lang not in FOOTERS:
        lang = "fr"

    body = render(template_text, row)
    footer = FOOTERS[lang].format(
        sender_name=CFG["SENDER_NAME"],
        sender_email=CFG["SENDER_EMAIL"],
        sender_address=CFG["SENDER_ADDRESS"],
    )

    msg = EmailMessage()
    msg["From"] = f'{CFG["SENDER_NAME"]} <{CFG["SENDER_EMAIL"]}>'
    msg["To"] = row["email"]
    msg["Subject"] = render(subject_line, row)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=CFG["SENDER_EMAIL"].split("@")[-1])
    if CFG.get("REPLY_TO"):
        msg["Reply-To"] = CFG["REPLY_TO"]
    # One-click unsubscribe headers. Gmail and Outlook surface these, which
    # measurably reduces the odds of being marked as spam.
    msg["List-Unsubscribe"] = f'<mailto:{CFG["SENDER_EMAIL"]}?subject=UNSUBSCRIBE>'
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg.set_content(body + footer)
    return msg


# ----------------------------------------------------------------- sending

def main():
    ap = argparse.ArgumentParser(description="web4you outreach sender")
    ap.add_argument("--send", action="store_true",
                    help="actually send. Without this flag nothing is transmitted.")
    ap.add_argument("--limit", type=int, default=0, help="cap the number of messages")
    ap.add_argument("--template", default="template_fr.txt",
                    help="fallback template when a row has no template column")
    ap.add_argument("--subject", default=None, help="override the subject line")
    ap.add_argument("--min-delay", type=float, default=25.0,
                    help="minimum seconds between sends (default 25)")
    ap.add_argument("--max-delay", type=float, default=70.0,
                    help="maximum seconds between sends (default 70)")
    ap.add_argument("--daily-cap", type=int, default=40,
                    help="refuse to exceed this many in one run (default 40)")
    ap.add_argument("--unsubscribe", metavar="EMAIL",
                    help="add an address to the suppression list and exit")
    args = ap.parse_args()

    if args.unsubscribe:
        add_suppression(args.unsubscribe)
        return

    load_config()

    if not PROSPECTS.exists():
        sys.exit(f"No {PROSPECTS.name}. See README.md.")

    suppressed = load_suppression()
    already = load_already_sent()

    with PROSPECTS.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    queue, skipped = [], []
    for row in rows:
        email = (row.get("email") or "").strip()
        name = row.get("business", "?")
        if not email:
            skipped.append((name, "no email address in the CSV"))
        elif "@" not in email or "." not in email.split("@")[-1]:
            skipped.append((name, f"malformed address: {email}"))
        elif email.lower() in suppressed:
            skipped.append((name, "on the suppression list"))
        elif email.lower() in already:
            skipped.append((name, "already emailed, see sent_log.csv"))
        elif (row.get("consent_basis") or "").strip() == "":
            skipped.append((name, "consent_basis column is empty -- see README"))
        else:
            queue.append(row)

    if args.limit:
        queue = queue[:args.limit]

    if len(queue) > args.daily_cap:
        print(f"Queue is {len(queue)}; capping at {args.daily_cap} for this run.")
        print("Sending hundreds at once is how a new domain gets blacklisted.")
        queue = queue[:args.daily_cap]

    print(f"\n{len(queue)} to send · {len(skipped)} skipped\n")
    if skipped:
        print("Skipped:")
        for name, why in skipped[:30]:
            print(f"  - {name}: {why}")
        if len(skipped) > 30:
            print(f"  ... and {len(skipped) - 30} more")
        print()

    if not queue:
        print("Nothing to do.")
        return

    default_tpl = (HERE / args.template).read_text(encoding="utf-8")
    subject_default = args.subject or CFG.get(
        "DEFAULT_SUBJECT", "Un site web pour {business}")

    # -------- dry run --------
    if not args.send:
        for row in queue:
            tpl_name = (row.get("template") or "").strip()
            tpl = (HERE / tpl_name).read_text(encoding="utf-8") if tpl_name else default_tpl
            try:
                msg = build_message(row, tpl, row.get("subject") or subject_default)
            except (ValueError, FileNotFoundError) as e:
                print(f"!! {row.get('business','?')}: {e}\n")
                continue
            print("=" * 72)
            print(f"To:      {msg['To']}")
            print(f"Subject: {msg['Subject']}")
            print("-" * 72)
            print(msg.get_content().rstrip())
            print()
        print("=" * 72)
        print(f"\nDRY RUN. Nothing was sent. Add --send when the previews look right.")
        return

    # -------- live --------
    print(f"LIVE SEND to {len(queue)} recipients.")
    if input("Type SEND to confirm: ").strip() != "SEND":
        print("Cancelled.")
        return

    port = int(CFG["SMTP_PORT"])
    ctx = ssl.create_default_context()
    ok = fail = 0

    try:
        if port == 465:
            server = smtplib.SMTP_SSL(CFG["SMTP_HOST"], port, context=ctx, timeout=30)
        else:
            server = smtplib.SMTP(CFG["SMTP_HOST"], port, timeout=30)
            server.starttls(context=ctx)
        server.login(CFG["SMTP_USER"], CFG["SMTP_PASS"])
    except Exception as e:
        sys.exit(f"SMTP connection failed: {e}")

    with server:
        for i, row in enumerate(queue, 1):
            tpl_name = (row.get("template") or "").strip()
            tpl = (HERE / tpl_name).read_text(encoding="utf-8") if tpl_name else default_tpl
            try:
                msg = build_message(row, tpl, row.get("subject") or subject_default)
                server.send_message(msg)
                log_sent(row, msg["Subject"], msg["Message-ID"])
                ok += 1
                print(f"[{i}/{len(queue)}] sent -> {row['email']} ({row.get('business','')})")
            except Exception as e:
                fail += 1
                print(f"[{i}/{len(queue)}] FAILED {row.get('email')}: {e}")

            if i < len(queue):
                pause = random.uniform(args.min_delay, args.max_delay)
                print(f"          waiting {pause:.0f}s")
                time.sleep(pause)

    print(f"\nDone. {ok} sent, {fail} failed. Log: {SENT_LOG.name}")
    print("Anyone who replies asking out goes in immediately:")
    print("  python send.py --unsubscribe their@address.com")


if __name__ == "__main__":
    main()
