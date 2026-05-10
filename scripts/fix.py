#!/usr/bin/env python3
"""Fix verification errors in formatted HTML files.

Usage:
    # Fix from a verification report
    python3 scripts/fix.py --report output/keilim-report.json

    # Fix with LLM re-generation (for hallucinated mishnayot)
    python3 scripts/fix.py --report output/keilim-report.json --backend anthropic

    # Dry run — show what would be fixed without changing files
    python3 scripts/fix.py --report output/keilim-report.json --dry-run

Reads a verification report JSON, classifies each error as:
    - programmatic: single-word replacements (wrong consonant, ending, etc.)
    - regen: missing mishnayot, inserted/deleted words, multi-word changes

Programmatic fixes are applied directly. Regen fixes require an LLM backend
(same options as format.py: ollama, anthropic, claude-code).

Without --backend, only programmatic fixes are applied and regen items are
listed for manual review.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from download import resolve_tractate
from verify import (MASECHET_FILENAMES, load_source_mishnayot,
                    load_html_mishnayot, extract_words, diff_words)
from format import (load_style_guides, build_system_prompt, build_user_prompt,
                    call_backend, clean_llm_response, DEFAULT_MODELS,
                    strip_sefaria_html)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_diffs(diffs):
    """Classify a mishna's diffs as 'programmatic' or 'regen'.

    Programmatic: all diffs are single-word replaces (1 source word → 1 html word).
    Everything else (inserts, deletes, multi-word replaces): regen.
    """
    if not diffs:
        return "ok"
    for d in diffs:
        if d["tag"] != "replace":
            return "regen"
        if len(d["source"]) != 1 or len(d["html"]) != 1:
            return "regen"
    return "programmatic"


# ---------------------------------------------------------------------------
# Word extraction with nikkud (for programmatic fixes)
# ---------------------------------------------------------------------------

def extract_nikkud_words(text):
    """Extract words keeping nikkud, stripping HTML tags and editorial marks."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('—', ' ')
    text = text.replace('״', '')
    text = text.replace('׳', '')
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'[:.;?!,]', ' ', text)
    words = [w.strip('.:,;?!-–—') for w in text.split()]
    return [w for w in words if w]


def strip_nikkud(word):
    """Remove nikkud for matching."""
    return re.sub(r'[\u0591-\u05C7]', '', word)


# ---------------------------------------------------------------------------
# Programmatic fix
# ---------------------------------------------------------------------------

def apply_programmatic_fix(html_text, source_text, diffs):
    """Fix single-word replacements in HTML mishna text.

    For each diff (1 normalized source word → 1 normalized html word),
    find the corresponding nikkud-bearing word in the HTML and replace
    it with the nikkud-bearing source word.

    Returns the fixed HTML text.
    """
    source_nikkud = extract_nikkud_words(source_text)
    html_nikkud = extract_nikkud_words(html_text)

    # Build normalized → nikkud mapping with positions
    source_norm = [strip_nikkud(w) for w in source_nikkud]
    html_norm = [strip_nikkud(w) for w in html_nikkud]

    # For each diff, find the wrong nikkud word and its replacement
    replacements = []  # (old_nikkud, new_nikkud)
    for d in diffs:
        wrong_norm = d["html"][0]
        right_norm = d["source"][0]

        # Find the nikkud version of the wrong word in HTML
        old_nikkud = None
        for i, w in enumerate(html_norm):
            if w == wrong_norm:
                old_nikkud = html_nikkud[i]
                break

        # Find the nikkud version of the right word in source
        new_nikkud = None
        for i, w in enumerate(source_norm):
            if w == right_norm:
                new_nikkud = source_nikkud[i]
                break

        if old_nikkud and new_nikkud and old_nikkud != new_nikkud:
            replacements.append((old_nikkud, new_nikkud))

    # Apply replacements to the raw HTML
    result = html_text
    for old, new in replacements:
        result = result.replace(old, new, 1)

    return result


# ---------------------------------------------------------------------------
# HTML patching
# ---------------------------------------------------------------------------

def patch_mishna_in_html(html_content, perek, mishna, new_text):
    """Replace a single mishna's text content in the full HTML file."""
    pattern = re.compile(
        r'(<div\s+class="mishna"\s+id="m' + str(perek) + '-' + str(mishna) +
        r'">\s*<p\s+class="mishna-label">.*?</p>\s*<p\s+class="mishna-text">\s*)'
        r'(.*?)'
        r'(\s*</p>\s*</div>)',
        re.DOTALL
    )
    match = pattern.search(html_content)
    if not match:
        return None
    return html_content[:match.start(2)] + new_text + html_content[match.end(2):]


def insert_mishna_in_html(html_content, perek, mishna, formatted_text):
    """Insert a missing mishna into the HTML file after the previous mishna."""
    from format import hebrew_numeral
    label = f"{hebrew_numeral(perek)}:{hebrew_numeral(mishna)}"
    new_div = (
        f'\n\n  <div class="mishna" id="m{perek}-{mishna}">\n'
        f'    <p class="mishna-label"><a id="mishna-{perek}-{mishna}"></a>'
        f'<b>{label}</b></p>\n'
        f'    <p class="mishna-text">\n'
        f'      {formatted_text}\n'
        f'    </p>\n'
        f'  </div>'
    )

    # Find the previous mishna or the perek header to insert after
    prev_mishna = mishna - 1
    if prev_mishna > 0:
        pattern = re.compile(
            r'(</div>)\s*(?=\n\n</div>|\n\n  <div class="mishna" id="m' +
            str(perek) + '-' + str(mishna + 1) + r'")',
            re.DOTALL
        )
        # Simpler: find the end of the previous mishna div
        prev_pattern = re.compile(
            r'(<div\s+class="mishna"\s+id="m' + str(perek) + '-' + str(prev_mishna) +
            r'">.*?</div>)',
            re.DOTALL
        )
        match = prev_pattern.search(html_content)
        if match:
            insert_pos = match.end()
            return html_content[:insert_pos] + new_div + html_content[insert_pos:]

    # Fallback: insert after perek header
    header_pattern = re.compile(
        r'(<h2 class="perek-title"><a id="perek-' + str(perek) + r'"></a>.*?</h2>)',
        re.DOTALL
    )
    match = header_pattern.search(html_content)
    if match:
        insert_pos = match.end()
        return html_content[:insert_pos] + new_div + html_content[insert_pos:]

    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fix verification errors in formatted HTML",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--report", required=True,
                        help="Path to verification report JSON")
    parser.add_argument("--backend", choices=["ollama", "anthropic", "claude-code"],
                        default=None,
                        help="LLM backend for regen fixes (omit to skip regen)")
    parser.add_argument("--model", default=None,
                        help="Model name (default depends on backend)")
    parser.add_argument("--base-url", default="http://localhost:11434",
                        help="Ollama API base URL")
    parser.add_argument("--dir", default=".", help="Base directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show plan without making changes")
    args = parser.parse_args()

    with open(args.report) as f:
        report = json.load(f)

    # Classify all errors
    plan = []  # list of (tractate_info, perek, mishna, category, diffs)
    for tr in report["tractates"]:
        tractate = tr["tractate"]
        seder = tr["seder"]
        if tr.get("html_missing"):
            continue
        for ch_str, mishnayot in tr.get("chapters", {}).items():
            ch = int(ch_str)
            for m in mishnayot:
                if m["status"] == "ok":
                    continue
                category = classify_diffs(m.get("diffs", []))
                if m["status"] == "missing":
                    category = "regen"
                plan.append({
                    "tractate": tractate,
                    "seder": seder,
                    "perek": ch,
                    "mishna": m["mishna"],
                    "category": category,
                    "status": m["status"],
                    "diffs": m.get("diffs", []),
                })

    if not plan:
        print("Nothing to fix.")
        return

    # Summary
    programmatic = [p for p in plan if p["category"] == "programmatic"]
    regen = [p for p in plan if p["category"] == "regen"]

    print(f"Fix plan: {len(plan)} issues")
    print(f"  {len(programmatic)} programmatic (word-level replacement)")
    print(f"  {len(regen)} regen (LLM re-format needed)")

    if args.dry_run:
        print("\nProgrammatic fixes (html → source):")
        for p in programmatic:
            diffs_desc = "; ".join(
                f"{' '.join(d['html'])} → {' '.join(d['source'])}"
                for d in p["diffs"]
            )
            print(f"  {p['tractate']} {p['perek']}:{p['mishna']} — {diffs_desc}")

        print("\nRegen needed:")
        for p in regen:
            if p["status"] == "missing":
                print(f"  {p['tractate']} {p['perek']}:{p['mishna']} — missing from HTML")
            else:
                n = sum(max(len(d['source']), len(d['html'])) for d in p['diffs'])
                print(f"  {p['tractate']} {p['perek']}:{p['mishna']} — "
                      f"{len(p['diffs'])} diffs, ~{n} words affected")
        return

    # Load LLM context if needed
    system_prompt = None
    model = None
    if args.backend and regen:
        editorial_guide, exemplar = load_style_guides()
        system_prompt = build_system_prompt(editorial_guide, exemplar)
        model = args.model or DEFAULT_MODELS[args.backend]
        print(f"\nRegen backend: {args.backend}, model: {model}")

    # Group by tractate for file I/O
    by_tractate = {}
    for p in plan:
        by_tractate.setdefault(p["tractate"], []).append(p)

    total_fixed = 0
    total_skipped = 0

    for tractate, items in by_tractate.items():
        seder = items[0]["seder"]
        filename = MASECHET_FILENAMES.get(tractate, tractate.lower())
        html_path = os.path.join(args.dir, "masechot", f"{filename}.html")

        with open(html_path) as f:
            html_content = f.read()

        modified = False

        for item in items:
            ref = f"{item['perek']}:{item['mishna']}"

            if item["category"] == "programmatic":
                # Load source text for this mishna
                source_texts = load_source_mishnayot(
                    seder, tractate, item["perek"], args.dir)
                if not source_texts or item["mishna"] > len(source_texts):
                    print(f"  ✗ {tractate} {ref} — source not found")
                    total_skipped += 1
                    continue

                source_text = source_texts[item["mishna"] - 1]
                source_clean = strip_sefaria_html(source_text)

                # Get current HTML mishna text
                html_mishnayot = load_html_mishnayot(tractate, args.dir)
                key = (item["perek"], item["mishna"])
                if key not in html_mishnayot:
                    print(f"  ✗ {tractate} {ref} — not in HTML")
                    total_skipped += 1
                    continue

                old_text = html_mishnayot[key]
                new_text = apply_programmatic_fix(old_text, source_clean,
                                                  item["diffs"])

                if new_text != old_text:
                    result = patch_mishna_in_html(html_content, item["perek"],
                                                  item["mishna"], new_text)
                    if result:
                        html_content = result
                        modified = True
                        diffs_desc = "; ".join(
                            f"{' '.join(d['html'])}→{' '.join(d['source'])}"
                            for d in item["diffs"]
                        )
                        print(f"  ✓ {tractate} {ref} — {diffs_desc}")
                        total_fixed += 1
                    else:
                        print(f"  ✗ {tractate} {ref} — could not patch HTML")
                        total_skipped += 1
                else:
                    print(f"  - {tractate} {ref} — no change needed")

            elif item["category"] == "regen":
                if not args.backend:
                    print(f"  ⊘ {tractate} {ref} — regen needed (no --backend)")
                    total_skipped += 1
                    continue

                # Load source text
                source_texts = load_source_mishnayot(
                    seder, tractate, item["perek"], args.dir)
                if not source_texts or item["mishna"] > len(source_texts):
                    print(f"  ✗ {tractate} {ref} — source not found")
                    total_skipped += 1
                    continue

                source_text = source_texts[item["mishna"] - 1]
                raw_text = strip_sefaria_html(source_text)

                print(f"  ↻ {tractate} {ref} — regenerating...", end=" ",
                      flush=True)

                try:
                    user_prompt = build_user_prompt(
                        raw_text, item["perek"], item["mishna"])
                    response = call_backend(args.backend, system_prompt,
                                            user_prompt, model, args.base_url)
                    formatted = clean_llm_response(response)

                    if item["status"] == "missing":
                        result = insert_mishna_in_html(
                            html_content, item["perek"], item["mishna"],
                            formatted)
                    else:
                        result = patch_mishna_in_html(
                            html_content, item["perek"], item["mishna"],
                            formatted)

                    if result:
                        html_content = result
                        modified = True
                        print("✓")
                        total_fixed += 1
                    else:
                        print("✗ could not patch")
                        total_skipped += 1
                except RuntimeError as e:
                    print(f"✗ {e}")
                    total_skipped += 1

        if modified:
            with open(html_path, "w") as f:
                f.write(html_content)
            print(f"  Written: {html_path}")

    print(f"\nDone: {total_fixed} fixed, {total_skipped} skipped")


if __name__ == "__main__":
    main()
