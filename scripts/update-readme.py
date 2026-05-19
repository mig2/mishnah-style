#!/usr/bin/env python3
"""Regenerate the Masechot table in README.md from HTML meta tags.

Usage:
    python3 scripts/update-readme.py
    python3 scripts/update-readme.py --dir /path/to/repo

Reads mishnah-style-version and formatted-date from each masechot/*.html,
groups by seder, and rewrites the ## Masechot section of README.md.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from download import SEDARIM

# Sefaria name → (display name, html filename)
MASECHET_DISPLAY = {
    "Berakhot": ("Brachot", "brachot"), "Peah": ("Peah", "peah"),
    "Demai": ("Demai", "demai"), "Kilayim": ("Kilayim", "kilayim"),
    "Sheviit": ("Sheviit", "sheviit"), "Terumot": ("Terumot", "terumot"),
    "Maasrot": ("Maaserot", "maaserot"), "Maaser_Sheni": ("Maaser Sheni", "maaser-sheni"),
    "Challah": ("Challah", "challah"), "Orlah": ("Orlah", "orlah"),
    "Bikkurim": ("Bikkurim", "bikkurim"), "Shabbat": ("Shabbat", "shabbat"),
    "Eruvin": ("Eruvin", "eruvin"), "Pesachim": ("Pesachim", "pesachim"),
    "Shekalim": ("Shekalim", "shekalim"), "Yoma": ("Yoma", "yoma"),
    "Sukkah": ("Sukkah", "sukkah"), "Beitzah": ("Beitzah", "beitzah"),
    "Rosh_Hashanah": ("Rosh Hashanah", "rosh-hashanah"),
    "Taanit": ("Taanit", "taanit"), "Megillah": ("Megillah", "megillah"),
    "Moed_Katan": ("Moed Katan", "moed-katan"),
    "Chagigah": ("Chagigah", "chagigah"), "Yevamot": ("Yevamot", "yevamot"),
    "Ketubot": ("Ketubot", "ketubot"), "Nedarim": ("Nedarim", "nedarim"),
    "Nazir": ("Nazir", "nazir"), "Sotah": ("Sotah", "sotah"),
    "Gittin": ("Gittin", "gittin"), "Kiddushin": ("Kiddushin", "kiddushin"),
    "Bava_Kamma": ("Bava Kamma", "bava-kamma"),
    "Bava_Metzia": ("Bava Metzia", "bava-metzia"),
    "Bava_Batra": ("Bava Batra", "bava-batra"),
    "Sanhedrin": ("Sanhedrin", "sanhedrin"), "Makkot": ("Makkot", "makkot"),
    "Shevuot": ("Shevuot", "shevuot"), "Eduyot": ("Eduyot", "eduyot"),
    "Avodah_Zarah": ("Avodah Zarah", "avodah-zarah"),
    "Avot": ("Avot", "avot"), "Horayot": ("Horayot", "horayot"),
    "Zevachim": ("Zevachim", "zevachim"), "Menachot": ("Menachot", "menachot"),
    "Chullin": ("Chullin", "chullin"), "Bekhorot": ("Bekhorot", "bekhorot"),
    "Arakhin": ("Arakhin", "arakhin"), "Temurah": ("Temurah", "temurah"),
    "Keritot": ("Keritot", "keritot"), "Meilah": ("Meilah", "meilah"),
    "Tamid": ("Tamid", "tamid"), "Middot": ("Middot", "middot"),
    "Kinnim": ("Kinnim", "kinnim"), "Kelim": ("Kelim", "keilim"),
    "Ohalot": ("Ohalot", "ohalot"), "Negaim": ("Negaim", "negaim"),
    "Parah": ("Parah", "parah"), "Taharot": ("Taharot", "taharot"),
    "Mikvaot": ("Mikvaot", "mikvaot"), "Niddah": ("Niddah", "niddah"),
    "Makhshirin": ("Makhshirin", "makhshirin"), "Zavim": ("Zavim", "zavim"),
    "Tevul_Yom": ("Tevul Yom", "tevul-yom"),
    "Yadayim": ("Yadayim", "yadayim"), "Oktzin": ("Uktzin", "uktzin"),
}


def read_meta(html_path):
    """Read version and date meta tags from an HTML file."""
    version = None
    date = None
    with open(html_path) as f:
        for line in f:
            m = re.search(r'mishnah-style-version.*?content="([^"]*)"', line)
            if m:
                version = m.group(1)
            m = re.search(r'formatted-date.*?content="([^"]*)"', line)
            if m:
                date = m.group(1)
            if version and date:
                break
    return version, date


def main():
    parser = argparse.ArgumentParser(
        description="Regenerate Masechot table in README.md")
    parser.add_argument("--dir", default=".", help="Base directory")
    args = parser.parse_args()

    readme_path = os.path.join(args.dir, "README.md")
    if not os.path.exists(readme_path):
        print(f"ERROR: {readme_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(readme_path) as f:
        readme = f.read()

    # Collect versions from all HTML files
    versions = {}  # (version, date) → count
    rows = []  # (seder, display_name, filename, version, date)

    for seder, tractates in SEDARIM.items():
        for sefaria_name, _ in tractates:
            display_name, filename = MASECHET_DISPLAY[sefaria_name]
            html_path = os.path.join(args.dir, "masechot", f"{filename}.html")

            if os.path.exists(html_path):
                version, date = read_meta(html_path)
                rows.append((seder, display_name, filename, version, date))
                if version and date:
                    versions[(version, date)] = versions.get((version, date), 0) + 1
            else:
                rows.append((seder, display_name, filename, None, None))

    # Build the table
    # Check if all files share the same version
    all_same = len(versions) == 1
    total = len(rows)
    present = sum(1 for _, _, _, v, _ in rows if v)

    lines = []
    lines.append("## Masechot")
    lines.append("")

    if all_same and present == total:
        v, d = list(versions.keys())[0]
        lines.append(f"All {total} masechot formatted. "
                     f"Last updated: [`{v}`](https://github.com/mig2/mishnah-style/tree/{v}) ({d}).")
        lines.append("")
        # Compact seder table (no per-file versions)
        lines.append("| Seder | Masechot |")
        lines.append("| --- | --- |")
        for seder, tractates in SEDARIM.items():
            links = []
            for sefaria_name, _ in tractates:
                display_name, filename = MASECHET_DISPLAY[sefaria_name]
                links.append(f"[{display_name}](masechot/{filename}.html)")
            lines.append(f"| {seder} | {', '.join(links)} |")
    else:
        # Detailed table with per-file versions
        lines.append(f"{present}/{total} masechot formatted.")
        lines.append("")
        lines.append("| Masechet | Version | Date |")
        lines.append("| --- | --- | --- |")
        for seder, display_name, filename, version, date in rows:
            if version:
                lines.append(
                    f"| [{display_name}](masechot/{filename}.html) "
                    f"| [`{version}`](https://github.com/mig2/mishnah-style/tree/{version}) "
                    f"| {date} |")
            else:
                lines.append(f"| {display_name} | — | — |")

    # Replace the section in README
    pattern = re.compile(
        r'(## Masechot\n).*?(\n## License)',
        re.DOTALL
    )
    new_section = '\n'.join(lines) + '\n'
    new_readme = pattern.sub(new_section + r'\n## License', readme)

    if new_readme == readme:
        print("No changes needed.")
        return

    with open(readme_path, "w") as f:
        f.write(new_readme)

    print(f"Updated {readme_path}")
    if all_same:
        v, d = list(versions.keys())[0]
        print(f"  All {total} masechot at {v} ({d})")
    else:
        print(f"  {len(versions)} distinct versions across {present} files")


if __name__ == "__main__":
    main()
