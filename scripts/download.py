#!/usr/bin/env python3
"""Download Mishnah text from Sefaria API v3.

Usage:
    python3 scripts/download.py masechet Berakhot
    python3 scripts/download.py seder Zeraim
    python3 scripts/download.py shas

Downloads raw JSON responses and stores them alongside a manifest
logging the URL, timestamp, and HTTP status for each request.

Output goes to sefaria/{seder}/{tractate}/ with one JSON file per chapter
and a manifest.jsonl file per tractate.
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

BASE_URL = "https://www.sefaria.org/api/v3/texts/Mishnah_{tractate}.{chapter}"

# Seder → list of (sefaria_name, chapter_count)
# Sefaria API names verified against MishnahTracker index and HTTP 200 checks.
# Chapter counts from MishnahTracker (MishnahIndex.json, 4181 mishnayot).
# Avot has 6 chapters on Sefaria (ch 6 = Kinyan Torah); MishnahTracker tracks 5.
SEDARIM = {
    "Zeraim": [
        ("Berakhot", 9),
        ("Peah", 8),
        ("Demai", 7),
        ("Kilayim", 9),
        ("Sheviit", 10),
        ("Terumot", 11),
        ("Maasrot", 5),
        ("Maaser_Sheni", 5),
        ("Challah", 4),
        ("Orlah", 3),
        ("Bikkurim", 4),
    ],
    "Moed": [
        ("Shabbat", 24),
        ("Eruvin", 10),
        ("Pesachim", 10),
        ("Shekalim", 8),
        ("Yoma", 8),
        ("Sukkah", 5),
        ("Beitzah", 5),
        ("Rosh_Hashanah", 4),
        ("Taanit", 4),
        ("Megillah", 4),
        ("Moed_Katan", 3),
        ("Chagigah", 3),
    ],
    "Nashim": [
        ("Yevamot", 16),
        ("Ketubot", 13),
        ("Nedarim", 11),
        ("Nazir", 9),
        ("Sotah", 9),
        ("Gittin", 9),
        ("Kiddushin", 4),
    ],
    "Nezikin": [
        ("Bava_Kamma", 10),
        ("Bava_Metzia", 10),
        ("Bava_Batra", 10),
        ("Sanhedrin", 11),
        ("Makkot", 3),
        ("Shevuot", 8),
        ("Eduyot", 8),
        ("Avodah_Zarah", 5),
        ("Avot", 6),
        ("Horayot", 3),
    ],
    "Kodashim": [
        ("Zevachim", 14),
        ("Menachot", 13),
        ("Chullin", 12),
        ("Bekhorot", 9),
        ("Arakhin", 9),
        ("Temurah", 7),
        ("Keritot", 6),
        ("Meilah", 6),
        ("Tamid", 7),
        ("Middot", 5),
        ("Kinnim", 3),
    ],
    "Taharot": [
        ("Kelim", 30),
        ("Ohalot", 18),
        ("Negaim", 14),
        ("Parah", 12),
        ("Taharot", 10),
        ("Mikvaot", 10),
        ("Niddah", 10),
        ("Makhshirin", 6),
        ("Zavim", 5),
        ("Tevul_Yom", 4),
        ("Yadayim", 4),
        ("Oktzin", 3),
    ],
}

# Aliases: common alternate spellings → canonical Sefaria name
_ALIASES = {
    "brachot": "Berakhot", "berachot": "Berakhot", "brachoth": "Berakhot",
    "maaserot": "Maasrot", "maserot": "Maasrot",
    "ohalot": "Ohalot", "oholot": "Ohalot",
    "uktzin": "Oktzin", "uktzim": "Oktzin",
    "keilim": "Kelim",
    "shvuot": "Shevuot", "shvuos": "Shevuot",
    "pesahim": "Pesachim",
    "bekhorot": "Bekhorot", "bechorot": "Bekhorot",
    "arachin": "Arakhin",
    "midot": "Middot",
    "keritut": "Keritot",
}

# Flat lookup: lowercase name → (seder, sefaria_name, chapters)
TRACTATE_LOOKUP = {}
for seder, tractates in SEDARIM.items():
    for sefaria_name, chapters in tractates:
        val = (seder, sefaria_name, chapters)
        key = sefaria_name.lower().replace("_", " ")
        TRACTATE_LOOKUP[key] = val
        TRACTATE_LOOKUP[sefaria_name.lower()] = val

# Add aliases
for alias, canonical in _ALIASES.items():
    if canonical in {name for _, names in SEDARIM.items() for name, _ in names}:
        for seder, tractates in SEDARIM.items():
            for sefaria_name, chapters in tractates:
                if sefaria_name == canonical:
                    TRACTATE_LOOKUP[alias] = (seder, sefaria_name, chapters)


def output_dir(seder, tractate):
    return os.path.join("sefaria", seder.lower(), tractate.lower())


def download_chapter(seder, tractate, chapter, base_dir):
    """Download a single chapter. Returns (url, status, filepath)."""
    url = BASE_URL.format(tractate=tractate, chapter=chapter)
    out_dir = os.path.join(base_dir, output_dir(seder, tractate))
    os.makedirs(out_dir, exist_ok=True)

    filepath = os.path.join(out_dir, f"chapter_{chapter}.json")

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            data = resp.read()
            with open(filepath, "wb") as f:
                f.write(data)
    except urllib.error.HTTPError as e:
        status = e.code
        filepath = None
    except Exception as e:
        print(f"  ERROR {tractate}.{chapter}: {e}", file=sys.stderr)
        status = 0
        filepath = None

    return url, status, filepath


def download_tractate(seder, tractate, chapters, base_dir):
    """Download all chapters of a tractate. Writes manifest.jsonl alongside."""
    out_dir = os.path.join(base_dir, output_dir(seder, tractate))
    os.makedirs(out_dir, exist_ok=True)
    manifest_path = os.path.join(out_dir, "manifest.jsonl")

    print(f"  {tractate} ({chapters} chapters)")

    with open(manifest_path, "w") as manifest:
        for ch in range(1, chapters + 1):
            url, status, filepath = download_chapter(seder, tractate, ch, base_dir)
            ts = datetime.now(timezone.utc).isoformat()
            entry = {
                "url": url,
                "status": status,
                "chapter": ch,
                "file": os.path.basename(filepath) if filepath else None,
                "timestamp": ts,
            }
            manifest.write(json.dumps(entry) + "\n")

            marker = "✓" if status == 200 else f"✗ ({status})"
            print(f"    ch {ch}: {marker}")

            # Be polite to Sefaria
            time.sleep(0.3)

    print(f"    manifest: {manifest_path}")


def resolve_tractate(name):
    """Resolve a user-provided tractate name to (seder, sefaria_name, chapters)."""
    key = name.lower().replace("_", " ").replace("-", " ")
    if key in TRACTATE_LOOKUP:
        return TRACTATE_LOOKUP[key]
    # Try with underscores
    key_under = name.lower().replace(" ", "_").replace("-", "_")
    if key_under in TRACTATE_LOOKUP:
        return TRACTATE_LOOKUP[key_under]
    # Fuzzy: check if any tractate starts with the input
    for k, v in TRACTATE_LOOKUP.items():
        if k.startswith(key):
            return v
    return None


def main():
    parser = argparse.ArgumentParser(description="Download Mishnah text from Sefaria")
    parser.add_argument("scope", choices=["masechet", "seder", "shas"],
                        help="What to download")
    parser.add_argument("name", nargs="?", default=None,
                        help="Tractate or seder name (not needed for shas)")
    parser.add_argument("--dir", default=".", help="Base directory (default: repo root)")
    args = parser.parse_args()

    base_dir = args.dir

    if args.scope == "shas":
        print("Downloading all of Shas")
        for seder, tractates in SEDARIM.items():
            print(f"\nSeder {seder}:")
            for tractate, chapters in tractates:
                download_tractate(seder, tractate, chapters, base_dir)

    elif args.scope == "seder":
        if not args.name:
            print("Usage: download.py seder <name>", file=sys.stderr)
            print(f"Available: {', '.join(SEDARIM.keys())}", file=sys.stderr)
            sys.exit(1)
        seder = args.name.capitalize()
        if seder not in SEDARIM:
            print(f"Unknown seder: {args.name}", file=sys.stderr)
            print(f"Available: {', '.join(SEDARIM.keys())}", file=sys.stderr)
            sys.exit(1)
        print(f"Downloading Seder {seder}")
        for tractate, chapters in SEDARIM[seder]:
            download_tractate(seder, tractate, chapters, base_dir)

    elif args.scope == "masechet":
        if not args.name:
            print("Usage: download.py masechet <name>", file=sys.stderr)
            sys.exit(1)
        result = resolve_tractate(args.name)
        if not result:
            print(f"Unknown tractate: {args.name}", file=sys.stderr)
            print("Try the Sefaria transliteration (e.g. Berakhot, Bava_Kamma, Oktzin)",
                  file=sys.stderr)
            sys.exit(1)
        seder, tractate, chapters = result
        print(f"Downloading {tractate} (Seder {seder})")
        download_tractate(seder, tractate, chapters, base_dir)

    print("\nDone.")


if __name__ == "__main__":
    main()
