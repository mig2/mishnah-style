#!/usr/bin/env python3
"""Verify formatted HTML against Sefaria source JSON.

Usage:
    python3 scripts/verify.py masechet Berakhot
    python3 scripts/verify.py masechet Berakhot --chapter 3
    python3 scripts/verify.py shas
    python3 scripts/verify.py shas --report output/report

Compares words in masechot/*.html against sefaria/{seder}/{tractate}/*.json
to detect hallucinated, missing, or altered text.

Reports:
    --report PATH   Write JSON report to PATH.json and HTML report to PATH.html

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
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from download import SEDARIM, resolve_tractate

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

# ---------------------------------------------------------------------------
# Word extraction and comparison
# ---------------------------------------------------------------------------

def strip_nikkud(text):
    """Remove nikkud (vowel points) for comparison."""
    return re.sub(r'[\u0591-\u05C7]', '', text)


def normalize_word(word):
    """Normalize a word for comparison: strip nikkud and punctuation."""
    word = strip_nikkud(word)
    word = word.strip('.:,;?!-–—')
    return word


def extract_words(text):
    """Extract normalized words from source or HTML text."""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('—', ' ')
    text = text.replace('״', '')
    text = text.replace('׳', '')
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'[:.;?!,]', ' ', text)
    text = ' '.join(text.split())
    words = [normalize_word(w) for w in text.split()]
    return [w for w in words if w]


def diff_words(source_words, html_words):
    """Compare two word lists. Returns list of diff dicts."""
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


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

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
    """Load and parse all mishnayot from the HTML file."""
    filename = MASECHET_FILENAMES.get(tractate, tractate.lower())
    html_path = os.path.join(base_dir, "masechot", f"{filename}.html")
    if not os.path.exists(html_path):
        return None
    with open(html_path) as f:
        html = f.read()

    mishnayot = {}
    pattern = re.compile(
        r'<div\s+class="mishna"\s+id="m(\d+)-(\d+)">\s*'
        r'<p\s+class="mishna-label">.*?</p>\s*'
        r'<p\s+class="mishna-text">\s*(.*?)\s*</p>',
        re.DOTALL
    )
    for match in pattern.finditer(html):
        perek = int(match.group(1))
        mishna = int(match.group(2))
        mishnayot[(perek, mishna)] = match.group(3)
    return mishnayot


# ---------------------------------------------------------------------------
# Verification (collects structured results)
# ---------------------------------------------------------------------------

def verify_mishna(source_text, html_text):
    """Verify a single mishna. Returns dict with status and diffs."""
    if html_text is None:
        return {"status": "missing", "diffs": []}
    source_words = extract_words(source_text)
    html_words = extract_words(html_text)
    diffs = diff_words(source_words, html_words)
    return {
        "status": "error" if diffs else "ok",
        "diffs": diffs,
    }


def verify_chapter(seder, tractate, chapter, html_mishnayot, base_dir="."):
    """Verify a chapter. Returns list of mishna results."""
    source_texts = load_source_mishnayot(seder, tractate, chapter, base_dir)
    if source_texts is None:
        return [{"mishna": 0, "status": "no_source", "diffs": []}]

    results = []
    for m_idx, source_text in enumerate(source_texts, 1):
        key = (chapter, m_idx)
        html_text = html_mishnayot.get(key)
        result = verify_mishna(source_text, html_text)
        result["mishna"] = m_idx
        results.append(result)
    return results


def verify_tractate(seder, tractate, num_chapters, chapters=None, base_dir="."):
    """Verify a tractate. Returns structured results dict."""
    if chapters is None:
        chapters = list(range(1, num_chapters + 1))

    html_mishnayot = load_html_mishnayot(tractate, base_dir)
    tractate_result = {
        "tractate": tractate,
        "seder": seder,
        "chapters": {},
        "total": 0,
        "errors": 0,
    }

    if html_mishnayot is None:
        filename = MASECHET_FILENAMES.get(tractate, tractate.lower())
        tractate_result["html_missing"] = True
        tractate_result["errors"] = 1
        return tractate_result

    for ch in chapters:
        ch_results = verify_chapter(seder, tractate, ch, html_mishnayot, base_dir)
        tractate_result["chapters"][ch] = ch_results
        for r in ch_results:
            tractate_result["total"] += 1
            if r["status"] != "ok":
                tractate_result["errors"] += 1

    return tractate_result


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

def print_results(results_list):
    """Print verification results to stdout."""
    grand_total = 0
    grand_errors = 0

    for tr in results_list:
        tractate = tr["tractate"]
        if tr.get("html_missing"):
            filename = MASECHET_FILENAMES.get(tractate, tractate.lower())
            print(f"\n{tractate}:")
            print(f"  ✗ HTML file not found: masechot/{filename}.html")
            grand_errors += 1
            continue

        print(f"\n{tractate}:")
        for ch_num, mishnayot in sorted(tr["chapters"].items()):
            print(f"  Chapter {ch_num}:")
            for m in mishnayot:
                ref = f"{ch_num}:{m['mishna']}"
                if m["status"] == "ok":
                    print(f"    ✓ {ref}")
                elif m["status"] == "missing":
                    print(f"    ✗ {ref} — missing from HTML")
                elif m["status"] == "no_source":
                    print(f"    ✗ No source JSON for chapter {ch_num}")
                else:
                    print(f"    ✗ {ref} — {len(m['diffs'])} difference(s)")
                    for d in m["diffs"]:
                        src = ' '.join(d['source'])
                        htm = ' '.join(d['html'])
                        if d['tag'] == 'delete':
                            print(f"        MISSING: {src}")
                        elif d['tag'] == 'insert':
                            print(f"        ADDED:   {htm}")
                        elif d['tag'] == 'replace':
                            print(f"        CHANGED: {src}  →  {htm}")

        grand_total += tr["total"]
        grand_errors += tr["errors"]

    clean = grand_total - grand_errors
    print(f"\n{'=' * 40}")
    print(f"Total: {grand_total} mishnayot, {clean} clean, {grand_errors} with differences")
    if grand_errors == 0:
        print("✓ All clear")
    else:
        print(f"✗ {grand_errors} mishnayot need review")


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------

def write_json_report(results_list, path):
    """Write structured JSON report."""
    # Convert chapter keys from int to str for JSON
    serializable = []
    for tr in results_list:
        tr_copy = dict(tr)
        if "chapters" in tr_copy:
            tr_copy["chapters"] = {str(k): v for k, v in tr_copy["chapters"].items()}
        serializable.append(tr_copy)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tractates": serializable,
        "summary": {
            "total": sum(t["total"] for t in results_list),
            "errors": sum(t["errors"] for t in results_list),
        },
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"JSON report: {path}")


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def write_html_report(results_list, path):
    """Write human-readable HTML report."""
    grand_total = sum(t["total"] for t in results_list)
    grand_errors = sum(t["errors"] for t in results_list)
    grand_clean = grand_total - grand_errors
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rows = []
    detail_sections = []

    for tr in results_list:
        tractate = tr["tractate"]
        if tr.get("html_missing"):
            rows.append(f'<tr class="err"><td>{tractate}</td>'
                        f'<td colspan="3">HTML file not found</td></tr>')
            continue

        t_total = tr["total"]
        t_errors = tr["errors"]
        t_clean = t_total - t_errors
        cls = "ok" if t_errors == 0 else "err"
        rows.append(f'<tr class="{cls}"><td>'
                     f'{"" if t_errors == 0 else "<a href=\"#" + tractate + "\">"}'
                     f'{tractate}'
                     f'{"" if t_errors == 0 else "</a>"}'
                     f'</td><td>{t_total}</td><td>{t_clean}</td>'
                     f'<td>{t_errors}</td></tr>')

        if t_errors > 0:
            issues = []
            for ch_num, mishnayot in sorted(tr["chapters"].items()):
                for m in mishnayot:
                    if m["status"] == "ok":
                        continue
                    ref = f"{ch_num}:{m['mishna']}"
                    if m["status"] == "missing":
                        issues.append(f'<div class="issue">'
                                      f'<span class="ref">{ref}</span> '
                                      f'<span class="tag missing">MISSING</span> '
                                      f'mishna not found in HTML</div>')
                    elif m["status"] == "no_source":
                        issues.append(f'<div class="issue">'
                                      f'<span class="ref">{ref}</span> '
                                      f'<span class="tag">NO SOURCE</span> '
                                      f'JSON not found</div>')
                    else:
                        for d in m["diffs"]:
                            src = ' '.join(d['source'])
                            htm = ' '.join(d['html'])
                            if d['tag'] == 'delete':
                                issues.append(
                                    f'<div class="issue">'
                                    f'<span class="ref">{ref}</span> '
                                    f'<span class="tag missing">MISSING</span> '
                                    f'<span class="hebrew">{src}</span></div>')
                            elif d['tag'] == 'insert':
                                issues.append(
                                    f'<div class="issue">'
                                    f'<span class="ref">{ref}</span> '
                                    f'<span class="tag added">ADDED</span> '
                                    f'<span class="hebrew">{htm}</span></div>')
                            elif d['tag'] == 'replace':
                                issues.append(
                                    f'<div class="issue">'
                                    f'<span class="ref">{ref}</span> '
                                    f'<span class="tag changed">CHANGED</span> '
                                    f'<span class="hebrew">{src}</span> → '
                                    f'<span class="hebrew">{htm}</span></div>')

            detail_sections.append(
                f'<div class="tractate-detail" id="{tractate}">'
                f'<h3>{tractate} — {t_errors} issue(s)</h3>'
                f'{"".join(issues)}</div>')

    summary_cls = "ok" if grand_errors == 0 else "err"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Mishnah Verification Report</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 60em;
       margin: 2em auto; padding: 0 1.5em; color: #1a1a1a; }}
h1 {{ font-size: 1.5rem; }}
h3 {{ font-size: 1.1rem; margin-top: 2em; border-bottom: 1px solid #ccc;
      padding-bottom: 0.3em; }}
.timestamp {{ color: #666; font-size: 0.9rem; }}
.summary {{ font-size: 1.2rem; padding: 0.8em; border-radius: 6px; margin: 1em 0; }}
.summary.ok {{ background: #e6f9e6; border: 1px solid #4a4; }}
.summary.err {{ background: #fde8e8; border: 1px solid #c44; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
th, td {{ padding: 0.4em 0.8em; text-align: left; border-bottom: 1px solid #eee; }}
th {{ background: #f5f5f5; font-weight: 600; }}
tr.ok td {{ color: #2a7a2a; }}
tr.err td {{ color: #a33; }}
tr.err td a {{ color: #a33; }}
.issue {{ padding: 0.3em 0; font-size: 0.95rem; }}
.ref {{ font-weight: 600; margin-right: 0.5em; }}
.tag {{ display: inline-block; font-size: 0.75rem; font-weight: 700;
        padding: 0.1em 0.4em; border-radius: 3px; margin-right: 0.3em;
        text-transform: uppercase; }}
.tag.missing {{ background: #fde8e8; color: #a33; }}
.tag.added {{ background: #fff3cd; color: #856404; }}
.tag.changed {{ background: #e8f0fe; color: #1a56db; }}
.hebrew {{ font-family: "SBL Hebrew", "Noto Serif Hebrew", serif;
           direction: rtl; unicode-bidi: isolate; }}
</style>
</head>
<body>
<h1>Mishnah Verification Report</h1>
<p class="timestamp">{ts}</p>

<div class="summary {summary_cls}">
  {grand_total} mishnayot checked — {grand_clean} clean, {grand_errors} with differences
</div>

<table>
<tr><th>Masechet</th><th>Total</th><th>Clean</th><th>Errors</th></tr>
{"".join(rows)}
</table>

{"".join(detail_sections)}

</body>
</html>
"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(html)
    print(f"HTML report: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Verify formatted HTML against Sefaria source JSON")
    parser.add_argument("scope", choices=["masechet", "shas"],
                        help="What to verify")
    parser.add_argument("name", nargs="?", default=None,
                        help="Tractate name (not needed for shas)")
    parser.add_argument("--chapter", type=int, default=None,
                        help="Verify only this chapter")
    parser.add_argument("--report", default=None,
                        help="Write reports to PATH.json and PATH.html")
    parser.add_argument("--dir", default=".", help="Base directory")
    args = parser.parse_args()

    results = []

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
        tr = verify_tractate(seder, tractate, num_chapters, chapters, args.dir)
        results.append(tr)

    elif args.scope == "shas":
        for seder, tractates in SEDARIM.items():
            print(f"\nSeder {seder}:")
            for tractate, num_chapters in tractates:
                print(f"  {tractate}...", end=" ", flush=True)
                tr = verify_tractate(seder, tractate, num_chapters,
                                     base_dir=args.dir)
                errors = tr["errors"]
                print(f"{'✓' if errors == 0 else f'✗ {errors} errors'}")
                results.append(tr)

    # Console output
    print_results(results)

    # File reports
    if args.report:
        write_json_report(results, args.report + ".json")
        write_html_report(results, args.report + ".html")

    # Exit code
    total_errors = sum(t["errors"] for t in results)
    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
