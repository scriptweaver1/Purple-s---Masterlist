#!/usr/bin/env python3
"""
Purple-Juice-4073 Audio Masterlist — Build Script
Fetches data from a published Google Sheet CSV and writes audios.json.
Run locally or via GitHub Actions.
"""

import csv
import json
import re
import sys
import urllib.request
from io import StringIO

# ─────────────────────────────────────────────────────────────
#  CONFIGURE THIS — paste your published Google Sheet CSV URL
#  File → Share → Publish to web → Sheet1 → CSV → Copy link
# ─────────────────────────────────────────────────────────────
SHEET_CSV_URL = "YOUR_GOOGLE_SHEET_CSV_URL_HERE"
OUTPUT_PATH   = "audios.json"
# ─────────────────────────────────────────────────────────────


def fetch_csv(url: str) -> list[dict]:
    print(f"Fetching: {url[:80]}…")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            content = r.read().decode("utf-8")
    except Exception as e:
        print(f"ERROR fetching CSV: {e}", file=sys.stderr)
        sys.exit(1)
    reader = csv.DictReader(StringIO(content))
    rows = list(reader)
    print(f"  → {len(rows)} rows, columns: {list(rows[0].keys()) if rows else '(empty)'}")
    return rows


def clean(val) -> str | None:
    """Return None for blank/placeholder values, stripped string otherwise."""
    if val is None:
        return None
    s = str(val).strip()
    if s.lower() in ("", "x", "nan", "none", "n/a", "#n/a"):
        return None
    return s


def parse_tags(raw) -> list[str]:
    """Extract [Tag] tokens from a cell."""
    if not raw:
        return []
    return [t.strip() for t in re.findall(r"\[([^\]]+)\]", str(raw)) if t.strip()]


def parse_bool(val) -> bool:
    s = str(val).strip()
    return s in ("1", "1.0", "true", "True", "yes")


def parse_date(val) -> str | None:
    s = clean(val)
    if not s:
        return None
    # Keep only the date portion (drop time if present)
    return s[:10]


def build_person(name_val, link_val) -> dict | None:
    name = clean(name_val)
    if not name:
        return None
    link = clean(link_val)
    return {"name": name, "link": link} if link else {"name": name}


def row_to_entry(row: dict) -> dict | None:
    """Convert one spreadsheet row to a JSON entry. Returns None for blank rows."""
    id_val = clean(row.get("ID", ""))
    title  = clean(row.get("Name", ""))

    # Skip blank/trailing rows
    if not id_val or not title or title.lower() == "nan":
        return None

    try:
        entry_id = int(float(id_val))
    except ValueError:
        print(f"  Skipping row with non-numeric ID: {id_val!r}")
        return None

    # Type — normalise to lowercase, default to romantic
    raw_type = clean(row.get("Type", "")) or ""
    entry_type = raw_type.lower() if raw_type else "romantic"

    # Collab partners (up to 3)
    collabs = []
    for i in range(1, 4):
        partner = build_person(
            row.get(f"Collab Partner {i} Name", ""),
            row.get(f"Collab Partner {i} Link", ""),
        )
        if partner:
            collabs.append(partner)

    return {
        "id":         entry_id,
        "title":      title,
        "tags":       parse_tags(row.get("Tags", "")),
        "synopsis":   clean(row.get("Synopsis", "")),
        "duration":   clean(row.get("Duration", "")),
        "audioLink":  clean(row.get("Audio Link", "")),
        "writer":     build_person(row.get("Writer Name", ""), row.get("Writer Link", "")),
        "type":       entry_type,
        "largeCollab": parse_bool(row.get("Large collab", "0")),
        "collabs":    collabs,
        "scriptLink": clean(row.get("Script Link", "")),
        "date":       parse_date(row.get("Date", "")),
        "editor":     build_person(row.get("Editor Name", ""), row.get("Editor Link", "")),
    }


def main():
    if SHEET_CSV_URL == "YOUR_GOOGLE_SHEET_CSV_URL_HERE":
        print("ERROR: Please set SHEET_CSV_URL in build_audios.py", file=sys.stderr)
        sys.exit(1)

    rows   = fetch_csv(SHEET_CSV_URL)
    audios = []

    for row in rows:
        entry = row_to_entry(row)
        if entry:
            audios.append(entry)

    # Stats
    from collections import Counter
    types = Counter(a["type"] for a in audios)
    print(f"\nBuilt {len(audios)} entries:")
    for t, n in sorted(types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {n}")
    print(f"  large collabs: {sum(1 for a in audios if a['largeCollab'])}")

    output = {"audios": audios}
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
