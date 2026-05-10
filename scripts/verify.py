#!/usr/bin/env python3
"""Verify formatted HTML against Sefaria source JSON.

Usage:
    python3 scripts/verify.py masechet Berakhot
    python3 scripts/verify.py masechet Berakhot --chapter 3
    python3 scripts/verify.py shas

Compares words in masechot/*.html against sefaria/{seder}/{tractate}/*.json
to detect hallucinated, missing, or altered text.

Requires:
    - Downloaded JSON (run scripts/download.py first)
    - Formatted HTML in masechot/
"""

import argparse
import difflib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from download import SEDARIM, resolve_tractate

# Masechet → HTML filename (duplicated from format.py to avoid circular import)
MASECHET_FILENAMES = {
    "Berakhot": "brachot", "Peah": "peah", "Demai": "demai",
    "Kilayim": "kilayim", "Sheviit": "sheviit", "Terumot": "terumot",
    "Maasrot": "maaserot", "Maaser_Sheni": "maaser-sheni",
    "Challah": "challah", "Orlah": "orlah", "Bikkurim": "bikkurim",
    "Shabbat": "shabbat", "Eruvin": "eruvin", "Pesachim": "pesachim",
    "Shekalim": "shekalim", "Yoma": "yoma", "Sukkah": "sukkah",
    "Beitzah": "beitzah", "Rosh_Hashanah": "rosh-hashanah",
    "Taanit": "taanit", "Megillah": "megillah", "Moed_Katan": "moed-katan",
    "Chagigah": "chagigah", "Yevamot": "yevamot", "Ketubot": "ketubot",
    "Nedarim": "nedarim", "Nazir": "nazir", "Sotah": "sotah",
    "Gittin": "gittin", "Kiddushin": "kiddushin",
    "Bava_Kamma": "bava-kamma", "Bava_Metzia": "bava-metzia",
    "Bava_Batra": "bava-batra", "Sanhedrin": "sanhedrin",
    "Makkot": "makkot", "Shevuot": "shevuot", "Eduyot": "eduyot",
    "Avodah_Zarah": "avodah-zarah", "Avot": "avot", "Horayot": "horayot",
    "Zevachim": "zevachim", "Menachot": "menachot", "Chullin": "chullin",
    "Bekhorot": "bekhorot", "Arakhin": "arakhin", "Temurah": "temurah",
    "Keritot": "keritot", "Meilah": "meilah", "Tamid": "tamid",
    "Middot": "middot", "Kinnim": "kinnim", "Kelim": "keilim",
    "Ohalot": "ohalot", "Negaim": "negaim", "Parah": "parah",
    "Taharot": "taharot", "Mikvaot": "mikvaot", "Niddah": "niddah",
    "Makhshirin": "makhshirin", "Zavim": "zavim",
    "Tevul_Yom": "tevul-yom", "Yadayim": "yadayim", "Oktzin": "uktzin",
}


def strip_nikkud(text):
    """Remove nikkud (vowel points) for comparison. Keeps consonants and letters."""
    # Hebrew nikkud range: U+0591–U+05C7
    return re.sub(r'[\u0591-\u05C7]', '', text)


def normalize_word(word):
    """Normalize a word for comparison: strip nikkud and punctuation."""
    word = strip_nikkud(word)
    word = word.strip('.:,;?!-–—')
    return word


def extract_words(text, is_html=False):
    """Extract normalized words from source or HTML text.

    For both source and HTML: strips HTML tags, editorial punctuation,
    nikkud, and normalizes for word-level comparison.
    """
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove em-dashes (editorial addition)
    text = text.replace('—', ' ')
    # Remove gershayim (editorial addition)
    text = text.replace('״', '')
    text = text.replace('׳', '')
    # Remove parenthetical references like (ויקרא יז)
    text = re.sub(r'\([^)]*\)', '', text)
    # Remove punctuation
    text = re.sub(r'[:.;?!,]', ' ', text)
    # Normalize whitespace
    text = ' '.join(text.split())
    words = [normalize_word(w) for w in text.split()]
    return [w for w in words if w]


def load_source_mishnayot(seder, tractate, chapter, base_dir="."):
    """Load source mishnayot from Sefaria JSON for a chapter."""
    json_path = os.path.join(base_dir, "sefaria", seder.lower(), tractate.lower(),
                             f"chapter_{chapter}.json")
    if not os.path.exists(json_path):
        return None
    with open(json_path) as f:
        data = json.load(f)
    return data["versions"][0]["text"]


def load_html_mishnayot(tractate, base_dir="."):
    """Load and parse all mishnayot from the HTML file.

    Returns dict: (perek, mishna) → raw HTML text content
    """
    filename = MASECHET_FILENAMES.get(tractate, tractate.lower())
    html_path = os.path.join(base_dir, "masechot", f"{filename}.html")
    if not os.path.exists(html_path):
        return None

    with open(html_path) as f:
        html = f.read()

    mishnayot = {}
    # Find each mishna-text block
    pattern = re.compile(
        r'<div\s+class="mishna"\s+id="m(\d+)-(\d+)">\s*'
        r'<p\s+class="mishna-label">.*?</p>\s*'
        r'<p\s+class="mishna-text">\s*(.*?)\s*</p>',
        re.DOTALL
    )
    for match in pattern.finditer(html):
        perek = int(match.group(1))
        mishna = int(match.group(2))
        text = match.group(3)
        mishnayot[(perek, mishna)] = text

    return mishnayot


def diff_words(source_words, html_words):
    """Compare two word lists. Returns list of (tag, words) tuples.

    Tags: 'equal', 'insert' (in HTML but not source), 'delete' (in source
    but not HTML), 'replace'.
    """
    matcher = difflib.SequenceMatcher(None, source_words, html_words)
    diffs = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue
        diffs.append({
            'tag': tag,
            'source': source_words[i1:i2],
            'html': html_words[j1:j2],
        })
    return diffs


def format_diff(diff):
    """Format a single diff entry for display."""
    tag = diff['tag']
    src = ' '.join(diff['source'])
    htm = ' '.join(diff['html'])
    if tag == 'delete':
        return f"  MISSING: {src}"
    elif tag == 'insert':
        return f"  ADDED:   {htm}"
    elif tag == 'replace':
        return f"  CHANGED: {src}  →  {htm}"
    return ""


def verify_chapter(seder, tractate, chapter, html_mishnayot, base_dir="."):
    """Verify a single chapter. Returns (total, errors) count."""
    source_texts = load_source_mishnayot(seder, tractate, chapter, base_dir)
    if source_texts is None:
        print(f"    ✗ No source JSON for chapter {chapter}")
        return 0, 1

    total = len(source_texts)
    errors = 0

    for m_idx, source_text in enumerate(source_texts, 1):
        key = (chapter, m_idx)
        if key not in html_mishnayot:
            print(f"    ✗ {chapter}:{m_idx} — missing from HTML")
            errors += 1
            continue

        source_words = extract_words(source_text)
        html_words = extract_words(html_mishnayot[key], is_html=True)
        diffs = diff_words(source_words, html_words)

        if diffs:
            print(f"    ✗ {chapter}:{m_idx} — {len(diffs)} difference(s)")
            for d in diffs:
                print(f"      {format_diff(d)}")
            errors += 1
        else:
            print(f"    ✓ {chapter}:{m_idx}")

    return total, errors


def verify_tractate(seder, tractate, num_chapters, chapters=None, base_dir="."):
    """Verify a tractate. Returns (total_mishnayot, total_errors)."""
    if chapters is None:
        chapters = list(range(1, num_chapters + 1))

    html_mishnayot = load_html_mishnayot(tractate, base_dir)
    if html_mishnayot is None:
        filename = MASECHET_FILENAMES.get(tractate, tractate.lower())
        print(f"  ✗ HTML file not found: masechot/{filename}.html")
        return 0, 1

    total_m = 0
    total_e = 0

    for ch in chapters:
        print(f"  Chapter {ch}:")
        t, e = verify_chapter(seder, tractate, ch, html_mishnayot, base_dir)
        total_m += t
        total_e += e

    return total_m, total_e


def main():
    parser = argparse.ArgumentParser(
        description="Verify formatted HTML against Sefaria source JSON")
    parser.add_argument("scope", choices=["masechet", "shas"],
                        help="What to verify")
    parser.add_argument("name", nargs="?", default=None,
                        help="Tractate name (not needed for shas)")
    parser.add_argument("--chapter", type=int, default=None,
                        help="Verify only this chapter")
    parser.add_argument("--dir", default=".", help="Base directory")
    args = parser.parse_args()

    if args.scope == "masechet":
        if not args.name:
            print("Usage: verify.py masechet <name>", file=sys.stderr)
            sys.exit(1)
        result = resolve_tractate(args.name)
        if not result:
            print(f"Unknown tractate: {args.name}", file=sys.stderr)
            sys.exit(1)
        seder, tractate, num_chapters = result
        chapters = [args.chapter] if args.chapter else None

        print(f"Verifying {tractate}")
        total_m, total_e = verify_tractate(seder, tractate, num_chapters,
                                           chapters, args.dir)

    elif args.scope == "shas":
        total_m = 0
        total_e = 0
        for seder, tractates in SEDARIM.items():
            print(f"\nSeder {seder}:")
            for tractate, num_chapters in tractates:
                print(f"\n{tractate}:")
                t, e = verify_tractate(seder, tractate, num_chapters,
                                       base_dir=args.dir)
                total_m += t
                total_e += e

    # Summary
    clean = total_m - total_e
    print(f"\n{'=' * 40}")
    print(f"Total: {total_m} mishnayot, {clean} clean, {total_e} with differences")
    if total_e == 0:
        print("✓ All clear")
    else:
        print(f"✗ {total_e} mishnayot need review")
        sys.exit(1)


if __name__ == "__main__":
    main()
