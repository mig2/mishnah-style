#!/usr/bin/env python3
"""Review pass: apply a decisions.json (from the review SPA, or hand-written) to
the durable KB — create entity stubs, append rejections, write disambiguation
rules. See docs/entities-detection.md.

Usage:
    python3 scripts/kb-promote.py entities/detect/decisions.json
    python3 scripts/kb-promote.py decisions.json --data entities/data --dry-run

decisions.json shape:
    {
      "accept": [ {kind, slug, type|term_type, names|term, variants, refs} , ...],
      "reject": [ {form, kind, scope, ref?, note?}, ... ],
      "rules":  [ {form, kind, resolve, scope, masechet?, ref?, note?}, ... ]
    }

accept -> entities/data/<folder>/<slug>.yaml as a `stub`
reject -> appended to entities/detect/rejections.yaml (deduped)
rules  -> appended to entities/detect/rules.yaml (deduped)

Re-running kb-detect afterwards resolves the promoted entities silently, suppresses
the rejections, and auto-applies the rules — so only the genuine delta resurfaces.

Requires: ruamel.yaml.
"""

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import kb_lib as kb
import kb_detect as engine
from ruamel.yaml.comments import CommentedMap, CommentedSeq

ROOT = SCRIPTS.parent
FOLDER = {"person": "people", "place": "places", "plant": "plants"}


def _cm(pairs):
    m = CommentedMap()
    for k, v in pairs:
        if v not in (None, [], {}):
            m[k] = v
    return m


def build_stub(d):
    """Build a valid stub entity (CommentedMap) from an accept decision."""
    kind = d["kind"]
    variants = CommentedSeq(d.get("variants") or [])
    refs = CommentedSeq(d.get("refs") or [])
    appearances = _cm([("mishnah", refs), ("other", CommentedSeq())])
    if kind == "plant":
        term = _cm([("he", d["term"]["he"]),
                    ("variants", CommentedSeq(d["term"].get("variants") or variants)),
                    ("en_common", d["term"].get("en_common"))])
        return _cm([("slug", d["slug"]), ("status", "stub"), ("term", term),
                    ("term_type", d.get("term_type", "species")),
                    ("appearances", appearances)])
    names = _cm([("he", d["names"]["he"]), ("en", d["names"].get("en")),
                 ("variants", variants)])
    return _cm([("slug", d["slug"]), ("status", "stub"), ("type", d["type"]),
                ("names", names), ("appearances", appearances)])


def append_unique(path, entries, key):
    """Append CommentedMap entries to a YAML list file, deduped by key()."""
    y = kb.make_yaml()
    data = y.load(path.read_text(encoding="utf-8")) if path.exists() else None
    if not isinstance(data, CommentedSeq) and not isinstance(data, list):
        data = CommentedSeq()
    seen = {key(e) for e in data}
    added = 0
    for e in entries:
        cm = CommentedMap(e)
        if key(cm) not in seen:
            data.append(cm)
            seen.add(key(cm))
            added += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        y.dump(data, f)
    return added


def main():
    ap = argparse.ArgumentParser(description="Apply review decisions to the KB.")
    ap.add_argument("decisions")
    ap.add_argument("--data", default=str(ROOT / "entities" / "data"))
    ap.add_argument("--detect", default=str(ROOT / "entities" / "detect"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    decisions = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
    data_dir, detect_dir = Path(args.data), Path(args.detect)

    created, skipped = [], []
    for d in decisions.get("accept", []):
        path = data_dir / FOLDER[d["kind"]] / f"{d['slug']}.yaml"
        if path.exists():
            skipped.append(d["slug"])
            continue
        if not args.dry_run:
            kb.save_entity(path, build_stub(d))
        created.append(d["slug"])

    rej_key = lambda r: (engine.normalize_form(r["form"]), r.get("kind"),
                         r.get("scope", "mishna"), r.get("ref"))
    rule_key = lambda r: (engine.normalize_form(r["form"]), r.get("kind"),
                          r.get("resolve"), r.get("scope", "global"), r.get("masechet"), r.get("ref"))
    n_rej = n_rule = 0
    if not args.dry_run:
        if decisions.get("reject"):
            n_rej = append_unique(detect_dir / "rejections.yaml", decisions["reject"], rej_key)
        if decisions.get("rules"):
            n_rule = append_unique(detect_dir / "rules.yaml", decisions["rules"], rule_key)

    print(f"{'(dry-run) ' if args.dry_run else ''}promoted:")
    print(f"  entities created: {len(created)} {created or ''}")
    if skipped:
        print(f"  skipped (already exist): {skipped}")
    print(f"  rejections added: {n_rej}")
    print(f"  rules added: {n_rule}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
