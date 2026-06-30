#!/usr/bin/env python3
"""Validate the entities knowledge base.

Usage:
    python3 scripts/kb-validate.py
    python3 scripts/kb-validate.py --data entities/data --schema entities/schema

Validation is the contract: a file that does not validate does not land
(wire this into a pre-commit hook and CI). See docs/entities-knowledge-base.md §11.

Two layers of checks:

  1. JSON Schema — every entities/data/**/*.yaml against its schema in
     entities/schema/ (people/ -> person, places/ -> place, plants/ -> plant),
     and sources.yaml against source.schema.json.

  2. Semantic cross-checks the schemas can't express:
       - every claim's `source` exists in data/sources.yaml
       - every mishnah appearance references a canonical masechet slug
         (from data/vocab/sedarim.yaml)
       - each entity file's stem matches its `slug`

  Cross-entity referential integrity (relationship/locale/alias slugs resolving
  to real files) is intentionally NOT enforced yet — entities accumulate over
  time and may reference not-yet-created stubs.

Exits non-zero if anything fails.

Requires: pyyaml, jsonschema (>=4.18).
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("kb-validate: PyYAML is required — pip install pyyaml")

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
except ImportError:
    sys.exit("kb-validate: jsonschema>=4.18 is required — pip install jsonschema")

ROOT = Path(__file__).resolve().parent.parent
FOLDER_SCHEMA = {"people": "person", "places": "place", "plants": "plant"}

# ANSI, but degrade gracefully when not a tty.
_TTY = sys.stdout.isatty()
GREEN = "\033[32m" if _TTY else ""
RED = "\033[31m" if _TTY else ""
DIM = "\033[2m" if _TTY else ""
RESET = "\033[0m" if _TTY else ""
OK = f"{GREEN}✓{RESET}"
BAD = f"{RED}✗{RESET}"


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_registry(schema_dir):
    """Load every *.schema.json into a registry keyed by its $id so that
    cross-file $refs (e.g. "claim.schema.json") resolve."""
    registry = Registry()
    schemas = {}
    for path in sorted(schema_dir.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        uri = schema.get("$id", path.name)
        registry = registry.with_resource(uri, Resource.from_contents(schema))
        schemas[path.name] = schema
    return registry, schemas


def iter_claims(node):
    """Yield every claim-shaped dict (any mapping carrying a `source` key)
    anywhere in the entity tree."""
    if isinstance(node, dict):
        if "source" in node and isinstance(node.get("source"), str):
            yield node
        for v in node.values():
            yield from iter_claims(v)
    elif isinstance(node, list):
        for v in node:
            yield from iter_claims(v)


def masechet_slugs(data_dir):
    sedarim = load_yaml(data_dir / "vocab" / "sedarim.yaml") or {}
    return {m["slug"] for masechtot in sedarim.values() for m in masechtot}


def schema_errors(instance, schema, registry):
    validator = Draft202012Validator(schema, registry=registry)
    out = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "(root)"
        out.append(f"{loc}: {err.message}")
    return out


def main():
    ap = argparse.ArgumentParser(description="Validate the entities knowledge base.")
    ap.add_argument("--data", default=str(ROOT / "entities" / "data"))
    ap.add_argument("--schema", default=str(ROOT / "entities" / "schema"))
    args = ap.parse_args()

    data_dir = Path(args.data)
    schema_dir = Path(args.schema)

    if not data_dir.is_dir() or not schema_dir.is_dir():
        sys.exit(f"kb-validate: missing data/ or schema/ dir ({data_dir}, {schema_dir})")

    registry, schemas = build_registry(schema_dir)
    sources = load_yaml(data_dir / "sources.yaml") or {}
    source_keys = set(sources)
    slugs = masechet_slugs(data_dir)

    files_ok = 0
    files_bad = 0

    def report(path, errors):
        nonlocal files_ok, files_bad
        try:
            rel = path.relative_to(ROOT)
        except ValueError:
            rel = path
        if errors:
            files_bad += 1
            print(f"{BAD} {rel}")
            for e in errors:
                print(f"    {DIM}- {e}{RESET}")
        else:
            files_ok += 1
            print(f"{OK} {rel}")

    # 1. sources.yaml against source.schema.json
    report(data_dir / "sources.yaml",
           schema_errors(sources, schemas["source.schema.json"], registry))

    # 2. each entity file
    for folder, kind in FOLDER_SCHEMA.items():
        sub = data_dir / folder
        if not sub.is_dir():
            continue
        schema = schemas[f"{kind}.schema.json"]
        for path in sorted(sub.glob("*.yaml")):
            doc = load_yaml(path)
            errors = schema_errors(doc, schema, registry)

            # semantic checks (only meaningful once the doc is a mapping)
            if isinstance(doc, dict):
                if doc.get("slug") != path.stem:
                    errors.append(
                        f"slug: '{doc.get('slug')}' does not match filename '{path.stem}'")
                for claim in iter_claims(doc):
                    src = claim.get("source")
                    if src not in source_keys:
                        errors.append(f"source '{src}' is not in sources.yaml")
                refs = (doc.get("appearances") or {}).get("mishnah") or []
                for ref in refs:
                    slug = ref.rsplit(" ", 1)[0]
                    if slug not in slugs:
                        errors.append(
                            f"appearance '{ref}': '{slug}' is not a canonical masechet slug")

            report(path, errors)

    # 3. durable detector artifacts (if present)
    detect_dir = data_dir.parent / "detect"
    for fname, schema_name in (("rejections.yaml", "rejection"), ("rules.yaml", "rule")):
        p = detect_dir / fname
        if p.exists():
            report(p, schema_errors(load_yaml(p), schemas[f"{schema_name}.schema.json"], registry))

    total = files_ok + files_bad
    print()
    if files_bad:
        print(f"{BAD} {files_bad}/{total} file(s) failed validation.")
        return 1
    print(f"{OK} all {total} file(s) valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
