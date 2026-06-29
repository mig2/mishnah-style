#!/usr/bin/env python3
"""Enrich copies of the masechot with the entity overlay (display phase 3).

Usage:
    python3 scripts/kb-enrich.py
    python3 scripts/kb-enrich.py --data entities/data --masechot masechot --out entities/site/read

The join (docs/entities-display.md §4, §6–8): for every mishna an entity appears
in, wrap the entity's surface form in the running text, link it to the phase-2
entity page, and add a CSS-only, per-type color overlay toggle (🌿 plants green,
📍 places red, 👤 people blue). The canonical masechot are NEVER modified — output
is a derived, gitignored copy under entities/site/read/.

Surface-form matching reuses verify.py's normalization (nikkud/final-letter/
double-vav folding) so a match survives vocalization, plus tolerance for a single
attached prefix letter (ה/ו/ב/כ/ל/מ/ש). This is the finicky part and is expected
to iterate (display spec §6); it is conservative — an unmarked word beats a wrong
link.

Requires: pyyaml (and scripts/verify.py for normalization).
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("kb-enrich: PyYAML is required — pip install pyyaml")

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent

# Normalization mirrors scripts/verify.py normalize_word (strip nikkud / punctuation,
# fold double-vav and divine name, normalize final letters). Inlined rather than
# imported because verify.py uses a Python 3.12-only f-string and won't parse here.
_FINAL_TO_REGULAR = str.maketrans("ךםןףץ", "כמנפצ")
_REGULAR_TO_FINAL = str.maketrans("כמנפצ", "ךםןףץ")


def _strip_nikkud(text):
    return re.sub(r"[֑-ׇ]", "", text)


def _normalize_final(word):
    if len(word) <= 1:
        return word
    return word[:-1].translate(_FINAL_TO_REGULAR) + word[-1].translate(_REGULAR_TO_FINAL)


def normalize_word(word):
    word = _strip_nikkud(word).strip(".:,;?!-–—'\"״׳*")
    word = word.replace("וו", "ו").replace("יי", "ה")
    return _normalize_final(word)
KINDS = {"people": "person", "places": "place", "plants": "plant"}
KIND_FOLDER = {"person": "people", "place": "places", "plant": "plants"}
PREFIXES = set("הובכלמש")          # single attached prefix letters tolerated
HEB_WORD = re.compile(r"[א-ת֑-ׇ]+")

OVERLAY_CSS = """
<style>
input.kb-ovl{position:absolute;left:-9999px;width:1px;height:1px;}
.kb-bar{position:sticky;top:0;z-index:10;display:flex;gap:.5rem;align-items:center;
 direction:ltr;background:#fff;border-bottom:1px solid #e6e6df;padding:.45rem .9rem;
 font-family:Georgia,serif;font-size:.85rem;}
.kb-bar .lbl{color:#6b6b66;margin-inline-end:.25rem;}
.kb-bar a{color:#2a5a8a;text-decoration:none;margin-inline-start:auto;}
label.kb-toggle{cursor:pointer;padding:.1rem .55rem;border:1px solid #ddd;border-radius:1rem;color:#333;}
.ent{color:inherit;text-decoration:none;}
.ent:hover{text-decoration:underline;}
#kb-plant:checked  ~ .kb-content .ent-plant {color:#2e7d32;}
#kb-place:checked  ~ .kb-content .ent-place {color:#c0392b;}
#kb-person:checked ~ .kb-content .ent-person{color:#2a5a8a;}
#kb-plant:checked  ~ .kb-bar label[for=kb-plant] {background:#e7f3e8;border-color:#2e7d32;}
#kb-place:checked  ~ .kb-bar label[for=kb-place] {background:#fbe9e7;border-color:#c0392b;}
#kb-person:checked ~ .kb-bar label[for=kb-person]{background:#e8eef6;border-color:#2a5a8a;}
</style>
"""

KB_BAR = """<input type="checkbox" class="kb-ovl" id="kb-plant">
<input type="checkbox" class="kb-ovl" id="kb-place">
<input type="checkbox" class="kb-ovl" id="kb-person">
<div class="kb-bar"><span class="lbl">Overlay:</span>
<label class="kb-toggle" for="kb-plant">🌿 plants</label>
<label class="kb-toggle" for="kb-place">📍 places</label>
<label class="kb-toggle" for="kb-person">👤 people</label>
<a href="{root}index.html">entities ↗</a></div>
<div class="kb-content">"""


def norm_form(text):
    return tuple(w for w in (normalize_word(x) for x in text.split()) if w)


def surface_forms(kind, doc):
    if kind == "plant":
        term = doc.get("term") or {}
        raw = [term.get("he")] + (term.get("variants") or [])
    else:
        names = doc.get("names") or {}
        raw = [names.get("he")] + (names.get("variants") or [])
    forms = {norm_form(r) for r in raw if r}
    return {f for f in forms if f}


def build_index(data_dir):
    """masechet-slug -> { (ch, mi): [ {kind, slug, forms} ] }."""
    index = {}
    for folder, kind in KINDS.items():
        for path in sorted((Path(data_dir) / folder).glob("*.yaml")):
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            forms = surface_forms(kind, doc)
            if not forms:
                continue
            for ref in (doc.get("appearances") or {}).get("mishnah") or []:
                slug, _, cm = ref.partition(" ")
                ch, _, mi = cm.partition(":")
                index.setdefault(slug, {}).setdefault((ch, mi), []).append(
                    {"kind": kind, "slug": path.stem, "forms": forms})
    return index


def _words_match(window, form):
    for i, (w, f) in enumerate(zip(window, form)):
        if w == f:
            continue
        if i == 0 and len(w) > 1 and w[0] in PREFIXES and w[1:] == f:  # attached prefix
            continue
        return False
    return True


def wrap_text_run(text, entities, root, counter):
    """Wrap entity surface forms found in a tag-free text run."""
    toks = [(m.group(), m.start(), m.end()) for m in HEB_WORD.finditer(text)]
    if not toks:
        return text
    norms = [normalize_word(t[0]) for t in toks]
    forms = sorted(((f, e["kind"], e["slug"]) for e in entities for f in e["forms"]),
                   key=lambda x: -len(x[0]))
    used = [False] * len(toks)
    spans = []
    for form, kind, slug in forms:
        L = len(form)
        for i in range(len(toks) - L + 1):
            if any(used[i:i + L]):
                continue
            if _words_match(norms[i:i + L], form):
                spans.append((toks[i][1], toks[i + L - 1][2], kind, slug))
                for j in range(i, i + L):
                    used[j] = True
    out = text
    for start, end, kind, slug in sorted(spans, key=lambda s: -s[0]):
        folder = KIND_FOLDER[kind]
        tag = f'<a class="ent ent-{kind}" href="{root}{folder}/{slug}.html">'
        out = out[:start] + tag + out[start:end] + "</a>" + out[end:]
        counter[kind] = counter.get(kind, 0) + 1
    return out


def wrap_inner(inner, entities, root, counter):
    """Wrap matches inside a mishna-text block, never touching HTML tags."""
    parts = re.split(r"(<[^>]+>)", inner)
    for i in range(0, len(parts), 2):
        parts[i] = wrap_text_run(parts[i], entities, root, counter)
    return "".join(parts)


def enrich_masechet(html, mishnayot, root, counter):
    for (ch, mi), entities in mishnayot.items():
        anchor = re.search(rf'id="m{ch}-{mi}"', html)
        if not anchor:
            continue
        block = re.search(r'(<p class="mishna-text">)(.*?)(</p>)', html[anchor.end():], re.S)
        if not block:
            continue
        start = anchor.end() + block.start(2)
        inner = block.group(2)
        html = html[:start] + wrap_inner(inner, entities, root, counter) + html[start + len(inner):]
    # overlay scaffolding
    html = html.replace("</head>", OVERLAY_CSS + "</head>", 1)
    html = html.replace("<body>", "<body>\n" + KB_BAR.format(root=root), 1)
    html = html.replace("</body>", "</div>\n</body>", 1)
    return html


def main():
    ap = argparse.ArgumentParser(description="Enrich masechot with the entity overlay.")
    ap.add_argument("--data", default=str(ROOT / "entities" / "data"))
    ap.add_argument("--masechot", default=str(ROOT / "masechot"))
    ap.add_argument("--out", default=str(ROOT / "entities" / "site" / "read"))
    args = ap.parse_args()

    index = build_index(args.data)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    root = "../"  # from site/read/<slug>.html up to site/

    pages = 0
    total = {}
    for slug in sorted(index):
        src = Path(args.masechot) / f"{slug}.html"
        if not src.exists():
            print(f"  skip {slug}: no masechet HTML")
            continue
        counter = {}
        enriched = enrich_masechet(src.read_text(encoding="utf-8"), index[slug], root, counter)
        (out / f"{slug}.html").write_text(enriched, encoding="utf-8")
        pages += 1
        marks = sum(counter.values())
        for k, v in counter.items():
            total[k] = total.get(k, 0) + v
        print(f"  {slug}.html: {marks} mention(s) {dict(counter)}")

    print(f"\nenriched {pages} masechet page(s) -> {out}")
    print(f"  marks by type: {total or '(none)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
