#!/usr/bin/env python3
"""Import place coordinates from Pleiades.

Usage:
    python3 scripts/kb-import-pleiades.py --slug tzippori
    python3 scripts/kb-import-pleiades.py --all --dry-run
    python3 scripts/kb-import-pleiades.py --slug tzippori --input fixture.json

Enriches places that carry an `ids.pleiades_id`, appending a coordinate claim
(source: pleiades) through the §8 upsert rules. Coordinate claims are
multi-valued — the Pleiades point is retained alongside any others as dissent.

Network note: the live fetch hits pleiades.stoa.org and needs a network policy
that allows it. Use `--input PATH` to run against saved JSON (offline).

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
PLEIADES_URL = "https://pleiades.stoa.org/places/{pid}/json"


def fetch(pid):
    req = urllib.request.Request(PLEIADES_URL.format(pid=pid),
                                 headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def transform(pl, data, conflicts):
    """Pleiades reprPoint is [lon, lat] (GeoJSON order)."""
    pt = pl.get("reprPoint")
    if not pt or len(pt) != 2:
        return []
    coord = kb.flow_map({"lat": pt[1], "lon": pt[0]})
    status = kb.upsert_claim(
        data, "geo.coordinates", coord, "pleiades", mode="multi",
        conflicts=conflicts, entity_slug=data.get("slug", ""),
        confidence="accepted", date=kb.today())
    return [("geo.coordinates", status)]


def main():
    ap = argparse.ArgumentParser(description="Enrich place coordinates from Pleiades.")
    ap.add_argument("--slug")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--input", help="Read Pleiades JSON from a file instead of fetching.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--data", default=str(ROOT / "entities" / "data"))
    args = ap.parse_args()

    sub = Path(args.data) / "places"
    if args.slug:
        paths = [sub / f"{args.slug}.yaml"]
    elif args.all:
        paths = sorted(sub.glob("*.yaml"))
    else:
        sys.exit("kb-import-pleiades: pass --slug or --all")

    conflicts = []
    changed = 0
    for path in paths:
        if not path.exists():
            print(f"  skip {path.name}: no such place")
            continue
        data = kb.load_entity(path)
        if data.get("geo") is None:
            print(f"  skip {path.name}: no geo block")
            continue
        pid = (data.get("ids") or {}).get("pleiades_id")
        if not pid:
            print(f"  skip {path.name}: no pleiades_id")
            continue
        pl = json.loads(Path(args.input).read_text()) if args.input else fetch(pid)
        log = transform(pl, data, conflicts)
        touched = [f"{f}={s}" for f, s in log if s != "unchanged"]
        if touched:
            changed += 1
            print(f"  {path.name} ({pid}): {', '.join(touched)}")
            if not args.dry_run:
                kb.save_entity(path, data)
        else:
            print(f"  {path.name} ({pid}): no change")

    print(f"\n{'(dry-run) ' if args.dry_run else ''}{changed} place(s) changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
