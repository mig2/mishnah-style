#!/usr/bin/env python3
"""Merge JSON-formatted mishnayot into masechet HTML files.

Usage:
    python3 scripts/merge.py output/keilim-fixes.json
    python3 scripts/merge.py output/keilim-formatted.json
    python3 scripts/merge.py output/*.json

Reads JSON files produced by format.py or fix.py and patches the
formatted mishnayot into the corresponding masechot/*.html files.

JSON format:
    {"tractate": "...", "mishnayot": [{"perek": N, "mishna": M, "formatted": "..."}]}

This is the only script that writes to masechot/.
"""

import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from format import hebrew_numeral, MASECHET_FILENAMES


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
    """Insert a missing mishna into the HTML file."""
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

    # Try to insert after the previous mishna
    prev_mishna = mishna - 1
    if prev_mishna > 0:
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


def perek_exists_in_html(html_content, perek):
    """Check whether a perek div exists in the HTML."""
    pattern = re.compile(r'<div\s+class="perek"\s+id="perek' + str(perek) + r'">')
    return bool(pattern.search(html_content))


def insert_perek_in_html(html_content, perek, mishnayot):
    """Insert an entire new perek with its mishnayot into the HTML.

    Also updates the TOC to include the new chapter link.
    """
    from format import ORDINALS, hebrew_numeral

    ordinal = ORDINALS[perek] if perek < len(ORDINALS) else str(perek)
    perek_label = hebrew_numeral(perek)

    # Build mishna divs
    mishna_divs = []
    for m in sorted(mishnayot, key=lambda x: x["mishna"]):
        label = f"{hebrew_numeral(perek)}:{hebrew_numeral(m['mishna'])}"
        mishna_divs.append(
            f'\n\n  <div class="mishna" id="m{perek}-{m["mishna"]}">\n'
            f'    <p class="mishna-label"><a id="mishna-{perek}-{m["mishna"]}"></a>'
            f'<b>{label}</b></p>\n'
            f'    <p class="mishna-text">\n'
            f'      {m["formatted"]}\n'
            f'    </p>\n'
            f'  </div>'
        )

    new_perek = (
        f'\n\n<div class="perek" id="perek{perek}">\n'
        f'  <h2 class="perek-title"><a id="perek-{perek}"></a>פרק {ordinal}</h2>'
        f'{"".join(mishna_divs)}\n\n'
        f'</div>'
    )

    # Insert before </body>
    body_end = html_content.rfind('</body>')
    if body_end == -1:
        return None
    html_content = html_content[:body_end] + new_perek + '\n\n' + html_content[body_end:]

    # Update TOC — add the new chapter link
    toc_link = f' <span class="sep">·</span> <a href="#perek-{perek}">{perek_label}</a>'
    # Find the last existing TOC link and append after it
    toc_pattern = re.compile(r'(<a href="#perek-\d+">[^<]+</a>)(\s*</nav>)')
    match = toc_pattern.search(html_content)
    if match:
        html_content = (html_content[:match.end(1)] + toc_link +
                        html_content[match.start(2):])

    return html_content


def mishna_exists_in_html(html_content, perek, mishna):
    """Check whether a mishna div exists in the HTML."""
    pattern = re.compile(
        r'<div\s+class="mishna"\s+id="m' + str(perek) + '-' + str(mishna) + r'">'
    )
    return bool(pattern.search(html_content))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Merge JSON-formatted mishnayot into masechet HTML files")
    parser.add_argument("inputs", nargs="+",
                        help="JSON files from format.py or fix.py")
    parser.add_argument("--dir", default=".", help="Base directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be merged without writing")
    args = parser.parse_args()

    # Expand globs (for shells that don't)
    input_files = []
    for pattern in args.inputs:
        expanded = glob.glob(pattern)
        if expanded:
            input_files.extend(expanded)
        else:
            input_files.append(pattern)

    # Load all JSON inputs, group by tractate
    by_tractate = {}  # tractate → list of {"perek", "mishna", "formatted"}
    for path in input_files:
        if not os.path.exists(path):
            print(f"WARNING: {path} not found, skipping", file=sys.stderr)
            continue
        with open(path) as f:
            data = json.load(f)
        tractate = data["tractate"]
        by_tractate.setdefault(tractate, []).extend(data["mishnayot"])

    if not by_tractate:
        print("No mishnayot to merge.")
        return

    total_patched = 0
    total_inserted = 0
    total_failed = 0

    for tractate, mishnayot in sorted(by_tractate.items()):
        filename = MASECHET_FILENAMES.get(tractate, tractate.lower())
        html_path = os.path.join(args.dir, "masechot", f"{filename}.html")

        if not os.path.exists(html_path):
            print(f"  ✗ {tractate}: {html_path} not found")
            total_failed += len(mishnayot)
            continue

        with open(html_path) as f:
            html_content = f.read()

        modified = False
        print(f"\n{tractate} ({len(mishnayot)} mishnayot):")

        # Group by perek to handle whole-chapter inserts
        by_perek = {}
        for m in mishnayot:
            by_perek.setdefault(m["perek"], []).append(m)

        for perek in sorted(by_perek.keys()):
            perek_mishnayot = sorted(by_perek[perek], key=lambda x: x["mishna"])

            if not perek_exists_in_html(html_content, perek):
                # Entire chapter is missing — insert whole perek
                if args.dry_run:
                    for m in perek_mishnayot:
                        print(f"  new-perek {perek}:{m['mishna']}")
                    continue

                result = insert_perek_in_html(html_content, perek, perek_mishnayot)
                if result:
                    html_content = result
                    modified = True
                    count = len(perek_mishnayot)
                    print(f"  ✓ chapter {perek} ({count} mishnayot, new perek)")
                    total_inserted += count
                else:
                    for m in perek_mishnayot:
                        print(f"  ✗ {perek}:{m['mishna']} — insert failed (no perek)")
                        total_failed += 1
                continue

            # Perek exists — handle individual mishnayot
            for m in perek_mishnayot:
                ref = f"{m['perek']}:{m['mishna']}"

                if args.dry_run:
                    exists = mishna_exists_in_html(html_content, m["perek"], m["mishna"])
                    action = "patch" if exists else "insert"
                    print(f"  {action} {ref}")
                    continue

                if mishna_exists_in_html(html_content, m["perek"], m["mishna"]):
                    result = patch_mishna_in_html(
                        html_content, m["perek"], m["mishna"], m["formatted"])
                    if result:
                        html_content = result
                        modified = True
                        print(f"  ✓ {ref} (patched)")
                        total_patched += 1
                    else:
                        print(f"  ✗ {ref} — patch failed")
                        total_failed += 1
                else:
                    result = insert_mishna_in_html(
                        html_content, m["perek"], m["mishna"], m["formatted"])
                    if result:
                        html_content = result
                        modified = True
                        print(f"  ✓ {ref} (inserted)")
                        total_inserted += 1
                    else:
                        print(f"  ✗ {ref} — insert failed")
                        total_failed += 1

        if modified and not args.dry_run:
            with open(html_path, "w") as f:
                f.write(html_content)
            print(f"  Written: {html_path}")

    if not args.dry_run:
        print(f"\nDone: {total_patched} patched, {total_inserted} inserted, "
              f"{total_failed} failed")


if __name__ == "__main__":
    main()
