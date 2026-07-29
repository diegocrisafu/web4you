#!/usr/bin/env python3
"""
Lint prospects.csv. Exits non-zero on anything that would misfire.

    python validate.py
"""
import csv
import sys
from pathlib import Path

REQUIRED = {
    "business", "contact_name", "email", "lang", "category",
    "area", "phone", "consent_basis", "template", "subject", "hook",
}

HERE = Path(__file__).parent


def main():
    path = HERE / "prospects.csv"
    if not path.exists():
        sys.exit("prospects.csv not found.")

    with path.open(encoding="utf-8-sig", newline="") as f:
        rdr = csv.DictReader(f)
        cols = set(rdr.fieldnames or [])
        rows = list(rdr)

    missing = REQUIRED - cols
    if missing:
        sys.exit(f"prospects.csv is missing columns: {sorted(missing)}")

    problems = []
    ready = 0
    seen = {}

    for i, r in enumerate(rows, start=2):
        name = (r.get("business") or "?").strip()

        if not name:
            problems.append(f"row {i}: blank business name")

        lang = (r.get("lang") or "fr").strip()
        if lang not in ("fr", "en"):
            problems.append(f"row {i} ({name}): lang is {lang!r}, must be fr or en")

        tpl = (r.get("template") or "").strip()
        if tpl and not (HERE / tpl).exists():
            problems.append(f"row {i} ({name}): template {tpl!r} does not exist")

        email = (r.get("email") or "").strip().lower()
        if not email:
            continue

        if "@" not in email or "." not in email.split("@")[-1]:
            problems.append(f"row {i} ({name}): malformed email {email!r}")
            continue

        if email in seen:
            problems.append(f"row {i} ({name}): duplicate of row {seen[email]}")
        seen[email] = i

        if not (r.get("consent_basis") or "").strip():
            problems.append(
                f"row {i} ({name}): has an email but consent_basis is blank. "
                "Record where you found the address."
            )
        else:
            ready += 1

    print(f"{len(rows)} rows | {ready} ready to send | {len(rows) - ready} incomplete")

    if problems:
        print("\nProblems:")
        for p in problems:
            print("  -", p)
        sys.exit(1)

    print("CSV is clean.")


if __name__ == "__main__":
    main()
