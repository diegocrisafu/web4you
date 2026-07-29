# Outreach sender

Bulk email for `prospects.csv`. Dry run is the default — nothing is transmitted
without `--send`.

```bash
cp .env.example .env        # fill in SMTP + your real name and mailing address
python send.py              # preview everything
python send.py --limit 3    # preview three
python send.py --send --limit 3
python send.py --unsubscribe someone@example.com
```

---

## Read this part before you send anything

You are in Quebec emailing Quebec businesses, so **CASL** applies — Canada's
Anti-Spam Legislation, one of the strictest in the world. It is not CAN-SPAM.
The difference matters:

| | US (CAN-SPAM) | Canada (CASL) |
|---|---|---|
| Consent | Opt-**out**. Send first, honour removal. | Opt-**in**. You need consent *before* sending. |
| Penalty | Per-message fines | Up to **$1M** for an individual, $10M for a business |

**The provision you're relying on is implied consent through conspicuous
publication.** CASL s.10(9)(b) grants implied consent where all three hold:

1. The address was **conspicuously published** by the business — on their own
   website, storefront, or public listing. Not scraped from a directory that
   aggregated it, and not guessed as `info@theirdomain.ca`.
2. It was **not accompanied by a statement** like "no unsolicited email."
3. Your message **relates to their business role**. Pitching a website to a
   shop owner qualifies. Pitching them a timeshare would not.

That's a real, usable basis. It is also the *only* thing standing between you
and a complaint, which is why `send.py` refuses to send any row whose
`consent_basis` column is blank. Fill it in with where you actually found the
address and the date you checked:

```
published on atelier-copai.ca/contact, checked 2026-07-29
```

That column is your evidence. Under CASL the **burden of proving consent is on
the sender**, not the complainant. If you can't write a sentence explaining
where the address came from, don't email that business — call them instead.

Every message must also carry your name, a valid mailing address, and a working
unsubscribe. `send.py` appends all three automatically and you cannot turn it
off. Requests to be removed must be honoured within 10 business days; use
`--unsubscribe` the same day and the question never comes up.

**Guessed addresses are the trap.** `info@`, `contact@`, and `bonjour@` invented
from a domain name are not conspicuously published. They are also how you end up
in a spam trap and get your domain blocked.

None of this is legal advice — I'm not a lawyer. The CRTC publishes plain-language
guidance at `crtc.gc.ca/eng/internet/anti.htm`, and it's worth twenty minutes.

---

## The bigger practical problem

**You don't have email addresses.** Google Places returns phone numbers, not
emails, so `prospects.csv` ships with that column empty and ten rows pre-filled
with everything else.

More to the point: the businesses on this list are largely run by people in their
fifties and sixties who do not read email. A 60-year-old ébéniste with eleven
Google reviews is not sitting in an inbox. Cold email to this segment converts
somewhere around nothing.

Where this script genuinely earns its keep:

- **Follow-up after you've walked in.** You met them, they took your card, you
  built the demo. Now the email lands in a context where it means something —
  and you have express consent, because they gave you the address.
- **The subset with real published addresses.** Caterers and clinics mostly do.
  Cabinetmakers and cobblers mostly don't.
- **Second and third touches** on people who showed interest.

Treat it as a follow-up tool, not a discovery tool. Discovery is the walk-in.

---

## Files

| File | What it is |
|---|---|
| `send.py` | The sender. Dry run unless `--send`. |
| `prospects.csv` | Your list. Ten rows pre-filled, `email` and `consent_basis` blank. |
| `template_fr.txt` / `template_en.txt` | Message bodies. `{field}` pulls from the CSV. |
| `suppression.txt` | Never-contact list. Committed on purpose so it survives. |
| `sent_log.csv` | Written on send. Prevents double-sends. Gitignored. |
| `.env` | SMTP credentials. **Gitignored — never commit this.** |

### CSV columns

`business` · `contact_name` · `email` · `lang` (`fr`/`en`) · `category` · `area` ·
`phone` · `consent_basis` **(required)** · `template` · `subject` · `hook`

`hook` is the one personalised clause, dropped into the sentence "Je vous écris
parce que {hook}." Keep it specific and observable — something from their reviews
or their listing. It is the only part of the message that proves you looked.

### Guard rails

- Dry run default
- Refuses to run while `.env` still holds placeholder text
- Skips blank `consent_basis`
- Skips malformed addresses
- Skips anyone in `suppression.txt` or already in `sent_log.csv`
- Caps at 40 per run (`--daily-cap`)
- Randomised 25–70s gap between sends
- Raises rather than shipping an unfilled `{merge_field}`
- Typed `SEND` confirmation before a live run
- Sets `List-Unsubscribe` headers, which measurably reduces spam-folder odds

Gmail's ceiling is roughly 500 recipients a day and sending anywhere near it from
a new account gets you flagged. Forty a day is plenty and looks human.
