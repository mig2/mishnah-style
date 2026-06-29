#!/usr/bin/env python3
"""Compile the entities knowledge base YAML into knowledge.db (SQLite).

Usage:
    python3 scripts/kb-build.py
    python3 scripts/kb-build.py --data entities/data --out entities/knowledge.db

The DB is a derived, regenerable index — never hand-edited; rebuild from
entities/data/. The build is deterministic and idempotent: it drops and
recreates everything from scratch, so the same YAML in produces the same DB out.
See docs/entities-knowledge-base.md §11.

Tables (flattened — they do not mirror the YAML nesting):
    source(key, citation, type, license, trust_tier)
    entity(slug, kind, type, status, he, en)
    claim(entity_slug, field, value_json, source, confidence,
          confirmed, asserted_by, asserted_date, note, extra_json)
    appearance(entity_slug, ref, work, masechet)
    external_id(entity_slug, authority, id)
Derived at build time:
    contemporaries(slug_a, slug_b, generation)   -- people sharing a generation
    cooccurrence(slug_a, slug_b, ref)            -- entities in the same mishna
    region_rollup(region, place_count)

Run scripts/kb-validate.py first; this build assumes valid input.

Requires: pyyaml.
"""

import argparse
import json
import sqlite3
import sys
from itertools import combinations
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("kb-build: PyYAML is required — pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
KINDS = {"people": "person", "places": "place", "plants": "plant"}
PROVENANCE_KEYS = {"value", "source", "confidence", "asserted_by", "date", "confirmed", "note"}

SCHEMA = """
CREATE TABLE source (
    key TEXT PRIMARY KEY, citation TEXT, type TEXT, license TEXT, trust_tier INTEGER
);
CREATE TABLE entity (
    slug TEXT PRIMARY KEY, kind TEXT, type TEXT, status TEXT, he TEXT, en TEXT
);
CREATE TABLE claim (
    entity_slug TEXT, field TEXT, value_json TEXT, source TEXT, confidence TEXT,
    confirmed INTEGER, asserted_by TEXT, asserted_date TEXT, note TEXT, extra_json TEXT
);
CREATE TABLE appearance (
    entity_slug TEXT, ref TEXT, work TEXT, masechet TEXT
);
CREATE TABLE external_id (
    entity_slug TEXT, authority TEXT, id TEXT
);
CREATE TABLE contemporaries (slug_a TEXT, slug_b TEXT, generation INTEGER);
CREATE TABLE cooccurrence (slug_a TEXT, slug_b TEXT, ref TEXT);
CREATE TABLE region_rollup (region TEXT, place_count INTEGER);
"""


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def jdump(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def walk_claims(node, path=()):
    """Yield (field, claim) for every claim-shaped mapping (carrying a string
    `source`). `field` is the dotted path to the key holding the claim list,
    e.g. 'bio', 'geo.coordinates', 'identification.candidates'."""
    if isinstance(node, dict):
        if isinstance(node.get("source"), str):
            yield ".".join(path), node
            return  # a claim is a leaf — don't descend into its `value`
        for key, val in node.items():
            yield from walk_claims(val, path + (key,))
    elif isinstance(node, list):
        for item in node:
            yield from walk_claims(item, path)


def he_en(kind, doc):
    if kind == "plant":
        term = doc.get("term") or {}
        return term.get("he"), term.get("en_common")
    names = doc.get("names") or {}
    return names.get("he"), names.get("en")


def entity_type(kind, doc):
    return doc.get("term_type") if kind == "plant" else doc.get("type")


def load_entities(data_dir):
    """Return a list of (kind, slug, doc) sorted by (kind, slug)."""
    out = []
    for folder, kind in KINDS.items():
        sub = data_dir / folder
        if not sub.is_dir():
            continue
        for path in sorted(sub.glob("*.yaml")):
            out.append((kind, path.stem, load_yaml(path)))
    return sorted(out, key=lambda t: (t[0], t[1]))


def build(data_dir, out_path):
    out_path = Path(out_path)
    if out_path.exists():
        out_path.unlink()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(out_path)
    db.executescript(SCHEMA)

    # sources
    sources = load_yaml(data_dir / "sources.yaml") or {}
    for key in sorted(sources):
        s = sources[key]
        db.execute(
            "INSERT INTO source VALUES (?,?,?,?,?)",
            (key, s.get("citation"), s.get("type"), s.get("license"), s.get("trust_tier")),
        )

    entities = load_entities(data_dir)
    # ref -> set of slugs, for co-occurrence; generation -> slugs, for contemporaries
    ref_entities, gen_people, region_counts = {}, {}, {}

    for kind, slug, doc in entities:
        he, en = he_en(kind, doc)
        db.execute(
            "INSERT INTO entity VALUES (?,?,?,?,?,?)",
            (slug, kind, entity_type(kind, doc), doc.get("status"), he, en),
        )

        for field, claim in walk_claims(doc):
            extra = {k: v for k, v in claim.items() if k not in PROVENANCE_KEYS}
            db.execute(
                "INSERT INTO claim VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    slug, field, jdump(claim.get("value")), claim.get("source"),
                    claim.get("confidence"), 1 if claim.get("confirmed") else 0,
                    claim.get("asserted_by"), claim.get("date"), claim.get("note"),
                    jdump(extra) if extra else None,
                ),
            )

        appearances = doc.get("appearances") or {}
        for work in ("mishnah", "other"):
            for ref in appearances.get(work) or []:
                masechet = ref.rsplit(" ", 1)[0] if work == "mishnah" else None
                db.execute(
                    "INSERT INTO appearance VALUES (?,?,?,?)", (slug, ref, work, masechet)
                )
                if work == "mishnah":
                    ref_entities.setdefault(ref, set()).add(slug)

        for authority, value in sorted((doc.get("ids") or {}).items()):
            if value is not None:
                db.execute(
                    "INSERT INTO external_id VALUES (?,?,?)", (slug, authority, str(value))
                )

        if kind == "person":
            gen = (doc.get("era") or {}).get("generation")
            if gen is not None:
                gen_people.setdefault(gen, []).append(slug)
        if kind == "place":
            region = (doc.get("geo") or {}).get("region") if doc.get("geo") else None
            if region:
                region_counts[region] = region_counts.get(region, 0) + 1

    # derived: contemporaries (same tannaitic generation)
    for gen in sorted(gen_people):
        for a, b in combinations(sorted(gen_people[gen]), 2):
            db.execute("INSERT INTO contemporaries VALUES (?,?,?)", (a, b, gen))

    # derived: co-occurrence (entities sharing a mishna ref)
    for ref in sorted(ref_entities):
        for a, b in combinations(sorted(ref_entities[ref]), 2):
            db.execute("INSERT INTO cooccurrence VALUES (?,?,?)", (a, b, ref))

    # derived: region rollup
    for region in sorted(region_counts):
        db.execute("INSERT INTO region_rollup VALUES (?,?)", (region, region_counts[region]))

    db.commit()
    counts = {
        t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("source", "entity", "claim", "appearance", "external_id",
                  "contemporaries", "cooccurrence", "region_rollup")
    }
    db.close()
    return counts


def main():
    ap = argparse.ArgumentParser(description="Compile the entities KB into knowledge.db.")
    ap.add_argument("--data", default=str(ROOT / "entities" / "data"))
    ap.add_argument("--out", default=str(ROOT / "entities" / "knowledge.db"))
    args = ap.parse_args()

    data_dir = Path(args.data)
    if not data_dir.is_dir():
        sys.exit(f"kb-build: data dir not found: {data_dir}")

    counts = build(data_dir, args.out)
    print(f"built {args.out}")
    for table, n in counts.items():
        print(f"  {table:<15} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
