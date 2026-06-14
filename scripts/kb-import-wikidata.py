#!/usr/bin/env python3
"""Import / enrich entities from Wikidata.

Usage:
    python3 scripts/kb-import-wikidata.py --kind people --slug akiva
    python3 scripts/kb-import-wikidata.py --kind places --all --dry-run
    python3 scripts/kb-import-wikidata.py --kind plants --slug chitah --input fixture.json

One writer among several (docs/entities-knowledge-base.md §10): it enriches
entities that already carry an `ids.wikidata_qid`, appending claims through the
§8 upsert rules. It never creates stubs and never overwrites confirmed claims.

Network note: the live fetch hits the Wikidata REST endpoint and needs a network
policy that allows wikidata.org. Use `--input PATH` to run the same transform
against a saved EntityData JSON (offline, e.g. the fixtures in entities/fixtures/).

Requires: ruamel.yaml (and network access, unless --input is used).
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kb_lib as kb

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "mishnah-style-kb/0.1 (https://github.com/mig2/mishnah-style)"
WIKIDATA_URL = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"

# Wikidata taxon-rank items (P105) -> rank label
RANKS = {"Q7432": "species", "Q34740": "genus", "Q35409": "family",
         "Q37517": "subspecies", "Q38829": "variety"}


def fetch(qid):
    req = urllib.request.Request(WIKIDATA_URL.format(qid=qid),
                                 headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _entity_blob(wd, qid):
    return (wd.get("entities") or {}).get(qid) or {}


def _label(blob, lang):
    return ((blob.get("labels") or {}).get(lang) or {}).get("value")


def _aliases(blob, lang):
    return [a.get("value") for a in (blob.get("aliases") or {}).get(lang, []) if a.get("value")]


def _claim_values(blob, prop):
    out = []
    for st in (blob.get("claims") or {}).get(prop, []):
        dv = ((st.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if dv is not None:
            out.append(dv)
    return out


def transform(kind, qid, wd, data, conflicts):
    """Apply Wikidata facts to `data`. Returns a list of (field, status)."""
    blob = _entity_blob(wd, qid)
    log = []
    d = kb.today()

    if kind == "person":
        desc = ((blob.get("descriptions") or {}).get("en") or {}).get("value")
        if desc:
            log.append(("bio", kb.upsert_claim(
                data, "bio", desc, "wikidata", mode="single", conflicts=conflicts,
                entity_slug=data.get("slug", ""), confidence="accepted", date=d)))
        variants = _aliases(blob, "he") + _aliases(blob, "en")
        if variants:
            n = kb.merge_variants(data, "names.variants", variants)
            log.append(("names.variants", f"+{n}" if n else "unchanged"))

    elif kind == "place":
        if data.get("geo") is not None:
            for v in _claim_values(blob, "P625"):
                coord = kb.flow_map({"lat": v.get("latitude"), "lon": v.get("longitude")})
                log.append(("geo.coordinates", kb.upsert_claim(
                    data, "geo.coordinates", coord, "wikidata", mode="multi",
                    conflicts=conflicts, entity_slug=data.get("slug", ""),
                    confidence="probable", date=d)))
        photos = _claim_values(blob, "P18")
        if photos and not (data.get("media") or {}).get("photo"):
            url = "https://commons.wikimedia.org/wiki/File:" + str(photos[0]).replace(" ", "_")
            data.setdefault("media", kb.CommentedMap())["photo"] = url
            log.append(("media.photo", "set"))

    elif kind == "plant":
        taxa = _claim_values(blob, "P225")
        rank_qids = _claim_values(blob, "P105")
        rank = RANKS.get((rank_qids[0] or {}).get("id")) if rank_qids else None
        for taxon in taxa:
            value = kb.flow_map({"taxon": taxon, "rank": rank or "species"})
            extra = {"ids": kb.flow_map({"wikidata_qid": qid})}
            log.append(("identification.candidates", kb.upsert_claim(
                data, "identification.candidates", value, "wikidata", mode="multi",
                conflicts=conflicts, entity_slug=data.get("slug", ""),
                confidence="probable", date=d, extra=extra)))

    return log


def targets(data_dir, kind, slug, want_all):
    folder = kb.KIND_DIR.get(kind, kind)
    sub = Path(data_dir) / folder
    if slug:
        return [sub / f"{slug}.yaml"]
    if want_all:
        return sorted(sub.glob("*.yaml"))
    sys.exit("kb-import-wikidata: pass --slug or --all")


def main():
    ap = argparse.ArgumentParser(description="Enrich entities from Wikidata.")
    ap.add_argument("--kind", required=True, choices=["people", "places", "plants"])
    ap.add_argument("--slug")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--qid", help="Taxon/entity QID to import. Required for plants "
                                  "(the QID lives on the candidate, not the term); "
                                  "overrides ids.wikidata_qid for people/places.")
    ap.add_argument("--input", help="Read EntityData JSON from a file instead of fetching.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--data", default=str(ROOT / "entities" / "data"))
    args = ap.parse_args()

    kind = kb.DIR_KIND[args.kind]
    conflicts = []
    changed = 0

    for path in targets(args.data, args.kind, args.slug, args.all):
        if not path.exists():
            print(f"  skip {path.name}: no such entity")
            continue
        data = kb.load_entity(path)
        qid = args.qid or (data.get("ids") or {}).get("wikidata_qid")
        if not qid:
            hint = " (plants need --qid)" if kind == "plant" else ""
            print(f"  skip {path.name}: no wikidata_qid{hint}")
            continue
        wd = json.loads(Path(args.input).read_text()) if args.input else fetch(qid)
        log = transform(kind, qid, wd, data, conflicts)
        touched = [f"{field}={status}" for field, status in log
                   if status not in ("unchanged", "0")]
        if touched:
            changed += 1
            print(f"  {path.name} ({qid}): {', '.join(touched)}")
            if not args.dry_run:
                kb.save_entity(path, data)
        else:
            print(f"  {path.name} ({qid}): no change")

    if conflicts:
        print(f"\n⚠ {len(conflicts)} conflict(s) with confirmed claims — NOT written:")
        for c in conflicts:
            print(f"    {c['entity']}.{c['field']}: kept {c['kept']!r}, rejected {c['rejected']!r}")
        if not args.dry_run:
            kb.write_conflicts(conflicts, ROOT / "entities" / "conflicts.log")

    print(f"\n{'(dry-run) ' if args.dry_run else ''}{changed} entit(ies) changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
