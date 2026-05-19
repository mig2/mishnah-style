#!/usr/bin/env python3
"""Fix verification errors, outputting JSON corrections.

Usage:
    # Programmatic fixes only (no LLM needed)
    python3 scripts/fix.py --report output/shas-report.json

    # Programmatic + LLM regen
    python3 scripts/fix.py --report output/shas-report.json --backend anthropic

    # Preview without writing
    python3 scripts/fix.py --report output/shas-report.json --dry-run

Reads a verification report JSON, classifies each error as:
    - programmatic: single-word replacements, inserts, deletes
    - regen: missing mishnayot, multi-word changes (needs LLM)

Outputs JSON files to output/ in the same format as format.py:
    {"tractate": "...", "mishnayot": [{"perek": N, "mishna": M, "formatted": "..."}]}

Use merge.py to apply the corrections into masechot/*.html.
"""

import argparse
import difflib
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

def is_programmatic_diff(d):
    """Check if a single diff is fixable programmatically."""
    if d["tag"] == "replace" and len(d["source"]) == 1 and len(d["html"]) == 1:
        return True
    if d["tag"] == "insert" and len(d["html"]) == 1:
        return True
    if d["tag"] == "delete" and len(d["source"]) == 1:
        return True
    return False


def classify_diffs(diffs):
    """Classify a mishna's diffs as 'programmatic', 'mixed', or 'regen'."""
    if not diffs:
        return "ok"
    has_programmatic = False
    has_regen = False
    for d in diffs:
        if is_programmatic_diff(d):
            has_programmatic = True
        else:
            has_regen = True
    if has_programmatic and not has_regen:
        return "programmatic"
    elif has_programmatic and has_regen:
        return "mixed"
    return "regen"


# ---------------------------------------------------------------------------
# Programmatic fix helpers
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


def find_nth_occurrence(text, word, n):
    """Find start position of Nth (0-based) occurrence of word in text."""
    pos = -1
    for _ in range(n + 1):
        pos = text.find(word, pos + 1)
        if pos == -1:
            return -1
    return pos


def apply_programmatic_fix(html_text, source_text):
    """Fix single-word diffs in HTML mishna text using positional alignment."""
    source_nikkud = extract_nikkud_words(source_text)
    html_nikkud = extract_nikkud_words(html_text)

    source_norm = [strip_nikkud(w) for w in source_nikkud]
    html_norm = [strip_nikkud(w) for w in html_nikkud]

    matcher = difflib.SequenceMatcher(None, source_norm, html_norm)

    fixes = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace" and (i2 - i1) == 1 and (j2 - j1) == 1:
            old = html_nikkud[j1]
            new = source_nikkud[i1]
            if old != new:
                fixes.append(("replace", j1, old, new))
        elif tag == "insert" and (j2 - j1) == 1:
            extra = html_nikkud[j1]
            fixes.append(("remove", j1, extra, None))
        elif tag == "delete" and (i2 - i1) == 1:
            missing = source_nikkud[i1]
            fixes.append(("add", j1, None, missing))

    if not fixes:
        return html_text

    result = html_text
    for fix_type, word_idx, old_nikkud, new_nikkud in reversed(fixes):
        if fix_type == "replace":
            occurrence = sum(1 for i in range(word_idx) if html_nikkud[i] == old_nikkud)
            pos = find_nth_occurrence(result, old_nikkud, occurrence)
            if pos != -1:
                result = result[:pos] + new_nikkud + result[pos + len(old_nikkud):]

        elif fix_type == "remove":
            occurrence = sum(1 for i in range(word_idx) if html_nikkud[i] == old_nikkud)
            pos = find_nth_occurrence(result, old_nikkud, occurrence)
            if pos != -1:
                end = pos + len(old_nikkud)
                if end < len(result) and result[end] == ' ':
                    end += 1
                elif pos > 0 and result[pos - 1] == ' ':
                    pos -= 1
                result = result[:pos] + result[end:]

        elif fix_type == "add":
            if word_idx < len(html_nikkud):
                anchor = html_nikkud[word_idx]
                occurrence = sum(1 for i in range(word_idx) if html_nikkud[i] == anchor)
                pos = find_nth_occurrence(result, anchor, occurrence)
                if pos != -1:
                    result = result[:pos] + new_nikkud + " " + result[pos:]
            else:
                result = result.rstrip() + " " + new_nikkud

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fix verification errors, output JSON corrections",
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
                        help="Show plan without writing")
    args = parser.parse_args()

    with open(args.report) as f:
        report = json.load(f)

    # Classify all errors
    plan = []
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

    programmatic = [p for p in plan if p["category"] == "programmatic"]
    mixed = [p for p in plan if p["category"] == "mixed"]
    regen = [p for p in plan if p["category"] == "regen"]

    print(f"Fix plan: {len(plan)} issues")
    print(f"  {len(programmatic)} programmatic (word-level)")
    print(f"  {len(mixed)} mixed (some programmatic, some regen)")
    print(f"  {len(regen)} regen (LLM needed)")

    if args.dry_run:
        print("\nProgrammatic fixes (html → source):")
        for p in programmatic + mixed:
            prog_diffs = [d for d in p["diffs"] if is_programmatic_diff(d)]
            if not prog_diffs:
                continue
            parts = []
            for d in prog_diffs:
                if d["tag"] == "replace":
                    parts.append(f"{d['html'][0]} → {d['source'][0]}")
                elif d["tag"] == "insert":
                    parts.append(f"remove «{d['html'][0]}»")
                elif d["tag"] == "delete":
                    parts.append(f"add «{d['source'][0]}»")
            tag = " (mixed)" if p["category"] == "mixed" else ""
            print(f"  {p['tractate']} {p['perek']}:{p['mishna']}{tag} — {'; '.join(parts)}")

        print("\nRegen needed:")
        for p in regen + mixed:
            regen_diffs = [d for d in p["diffs"] if not is_programmatic_diff(d)]
            if p["status"] == "missing":
                print(f"  {p['tractate']} {p['perek']}:{p['mishna']} — missing from HTML")
            elif regen_diffs:
                n = sum(max(len(d['source']), len(d['html'])) for d in regen_diffs)
                tag = " (mixed)" if p["category"] == "mixed" else ""
                print(f"  {p['tractate']} {p['perek']}:{p['mishna']}{tag} — "
                      f"{len(regen_diffs)} diffs, ~{n} words affected")
        return

    # Load LLM context if needed
    system_prompt = None
    model = None
    if args.backend and (regen or mixed):
        editorial_guide, exemplar = load_style_guides()
        system_prompt = build_system_prompt(editorial_guide, exemplar)
        model = args.model or DEFAULT_MODELS[args.backend]
        print(f"\nRegen backend: {args.backend}, model: {model}")

    # Group by tractate
    by_tractate = {}
    for p in plan:
        by_tractate.setdefault(p["tractate"], []).append(p)

    # Collect JSON output per tractate
    output_by_tractate = {}  # tractate → list of {"perek", "mishna", "formatted"}
    total_fixed = 0
    total_skipped = 0

    for tractate, items in by_tractate.items():
        seder = items[0]["seder"]
        html_mishnayot = load_html_mishnayot(tractate, args.dir)

        for item in items:
            ref = f"{item['perek']}:{item['mishna']}"

            if item["category"] in ("programmatic", "mixed"):
                source_texts = load_source_mishnayot(
                    seder, tractate, item["perek"], args.dir)
                if not source_texts or item["mishna"] > len(source_texts):
                    print(f"  ✗ {tractate} {ref} — source not found")
                    total_skipped += 1
                    continue

                source_text = source_texts[item["mishna"] - 1]
                source_clean = strip_sefaria_html(source_text)

                key = (item["perek"], item["mishna"])
                if html_mishnayot and key in html_mishnayot:
                    old_text = html_mishnayot[key]
                    new_text = apply_programmatic_fix(old_text, source_clean)

                    if new_text != old_text:
                        output_by_tractate.setdefault(tractate, []).append({
                            "perek": item["perek"],
                            "mishna": item["mishna"],
                            "formatted": new_text,
                        })
                        prog_diffs = [d for d in item["diffs"] if is_programmatic_diff(d)]
                        parts = []
                        for d in prog_diffs:
                            if d["tag"] == "replace":
                                parts.append(f"{d['html'][0]}→{d['source'][0]}")
                            elif d["tag"] == "insert":
                                parts.append(f"remove «{d['html'][0]}»")
                            elif d["tag"] == "delete":
                                parts.append(f"add «{d['source'][0]}»")
                        tag = " (mixed)" if item["category"] == "mixed" else ""
                        print(f"  ✓ {tractate} {ref}{tag} — {'; '.join(parts)}")
                        total_fixed += 1
                    else:
                        print(f"  - {tractate} {ref} — no change needed")
                else:
                    print(f"  ✗ {tractate} {ref} — not in HTML")
                    total_skipped += 1

            if item["category"] in ("regen", "mixed"):
                # Check if there are regen diffs remaining
                regen_diffs = [d for d in item["diffs"] if not is_programmatic_diff(d)]
                if not regen_diffs and item["status"] != "missing":
                    continue

                if not args.backend:
                    print(f"  ⊘ {tractate} {ref} — regen needed (no --backend)")
                    total_skipped += 1
                    continue

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

                    output_by_tractate.setdefault(tractate, []).append({
                        "perek": item["perek"],
                        "mishna": item["mishna"],
                        "formatted": formatted,
                    })
                    print("✓")
                    total_fixed += 1
                except RuntimeError as e:
                    print(f"✗ {e}")
                    total_skipped += 1

    # Write JSON output per tractate
    if output_by_tractate:
        out_dir = os.path.join(args.dir, "output")
        os.makedirs(out_dir, exist_ok=True)

        for tractate, mishnayot in output_by_tractate.items():
            filename = MASECHET_FILENAMES.get(tractate, tractate.lower())
            out_path = os.path.join(out_dir, f"{filename}-fixes.json")
            output = {
                "tractate": tractate,
                "mishnayot": mishnayot,
            }
            with open(out_path, "w") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            print(f"  Written: {out_path} ({len(mishnayot)} corrections)")

    print(f"\nDone: {total_fixed} fixed, {total_skipped} skipped")


if __name__ == "__main__":
    main()
