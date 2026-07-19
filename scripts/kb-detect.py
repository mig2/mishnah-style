#!/usr/bin/env python3
"""Identity pass: detect people/places/plants mishna-by-mishna and resolve each
against the KB, rejections, and rules (display: docs/entities-detection.md).

Usage:
    # deterministic (offline): people from the bolded names already in masechot/
    python3 scripts/kb-detect.py --mode bold
    python3 scripts/kb-detect.py --mode bold --masechet makkot --dry-run
    # llm sweep (needs network + an LLM backend; runs on your machine)
    python3 scripts/kb-detect.py --mode llm --backend anthropic

For each mention the engine (kb_detect.Resolver) returns:
  known     -> append `{ref}` to that entity's appearances (source: detector), silently
  rejected  -> suppressed
  ambiguous -> queued for review (candidates, or a rule resolves it)
  new       -> a proposal (grouped by normalized form; refs accrue across the run)

Output: entities/detect/proposals.json — the mishna-ordered review surface for the
SPA. Known appearances are written straight to the entity YAML (idempotent).

Requires: pyyaml. --mode llm needs a backend (claude-code, anthropic, or ollama).
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("kb-detect: PyYAML is required — pip install pyyaml")

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import kb_detect as engine
import kb_lib as kb

ROOT = SCRIPTS.parent
KINDS = {"people": "person", "places": "place", "plants": "plant"}


def entity_forms(kind, doc):
    if kind == "plant":
        term = doc.get("term") or {}
        return [term.get("he")] + (term.get("variants") or [])
    names = doc.get("names") or {}
    return [names.get("he")] + (names.get("variants") or [])


def load_entities(data_dir):
    out = []
    for folder, kind in KINDS.items():
        for path in sorted((Path(data_dir) / folder).glob("*.yaml")):
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            out.append({"kind": kind, "slug": path.stem,
                        "forms": [f for f in entity_forms(kind, doc) if f], "path": path, "doc": doc})
    return out


def load_yaml_list(path):
    if not Path(path).exists():
        return []
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []


# --- LLM detection: ask the model to identify entities -----------------------

_LLM_SYSTEM = """You are a Mishnah entity extractor. Given raw Mishnah text, identify all:
- **people**: named rabbis, tannaim, biblical figures, any named person
- **places**: cities, regions, geographic locations, buildings (Temple areas, etc.)
- **plants**: crops, trees, botanical items mentioned by name

Return ONLY a JSON array of objects, each with "form" (the Hebrew text as it appears) and "kind" (one of: person, place, plant). No explanation, no markdown fences.

Example output:
[{"form": "רַבִּי עֲקִיבָא", "kind": "person"}, {"form": "יְרוּשָׁלַיִם", "kind": "place"}, {"form": "חִטִּים", "kind": "plant"}]

If no entities are found, return: []
Do NOT include generic terms (e.g. "אדם", "איש", "מקום") — only specific named entities."""


def detect_llm(masechot_dir, slugs, backend, model, base_url):
    """Yield (ref, [(form, kind), ...]) for every mishna, using LLM extraction."""
    from format import call_backend, DEFAULT_MODELS

    if model is None:
        model = DEFAULT_MODELS.get(backend)

    for slug in slugs:
        src = Path(masechot_dir) / f"{slug}.html"
        if not src.exists():
            continue
        html = src.read_text(encoding="utf-8")
        for ch, mi, text in _MISHNA.findall(html):
            # Strip HTML to get plain text for the LLM
            plain = _TAG.sub("", text).replace("—", " ").strip()
            plain = re.sub(r"\s+", " ", plain)
            if not plain:
                continue

            ref = f"{slug} {ch}:{mi}"
            user_prompt = f"Extract entities from this mishna ({ref}):\n\n{plain}"

            try:
                response = call_backend(backend, _LLM_SYSTEM, user_prompt,
                                        model, base_url)
                # Parse JSON response
                response = response.strip()
                if response.startswith("```"):
                    response = re.sub(r"^```(?:json)?\s*", "", response)
                    response = re.sub(r"\s*```$", "", response)
                entities = json.loads(response)
                mentions = [(e["form"], e["kind"]) for e in entities
                            if "form" in e and "kind" in e
                            and e["kind"] in ("person", "place", "plant")]
                if mentions:
                    yield ref, mentions
            except (json.JSONDecodeError, KeyError, RuntimeError) as exc:
                print(f"  ⚠ {ref}: {exc}", file=sys.stderr)
                continue


# --- deterministic detection: bolded rabbinic names in the masechot -----------
_MISHNA = re.compile(r'id="m(\d+)-(\d+)".*?<p class="mishna-text">(.*?)</p>', re.S)
_BOLD = re.compile(r"<b>(.*?)</b>", re.S)
_TAG = re.compile(r"<[^>]+>")


def detect_bold(masechot_dir, slugs):
    """Yield (ref, [(form, kind), ...]) for every mishna with bold names."""
    for slug in slugs:
        src = Path(masechot_dir) / f"{slug}.html"
        if not src.exists():
            continue
        html = src.read_text(encoding="utf-8")
        for ch, mi, text in _MISHNA.findall(html):
            mentions = []
            for span in _BOLD.findall(text):
                form = _TAG.sub("", span).strip()
                if form:
                    mentions.append((form, "person"))
            if mentions:
                yield f"{slug} {ch}:{mi}", mentions


def main():
    ap = argparse.ArgumentParser(description="Detect entities mishna-by-mishna.")
    ap.add_argument("--mode", choices=["bold", "llm"], default="bold")
    ap.add_argument("--backend", help="LLM backend (anthropic/ollama/claude-code) for --mode llm")
    ap.add_argument("--model", default=None, help="Model name (default depends on backend)")
    ap.add_argument("--base-url", default="http://localhost:11434", help="Ollama API base URL")
    ap.add_argument("--masechet", action="append", help="limit to these masechet slug(s)")
    ap.add_argument("--data", default=str(ROOT / "entities" / "data"))
    ap.add_argument("--masechot", default=str(ROOT / "masechot"))
    ap.add_argument("--out", default=str(ROOT / "entities" / "detect" / "proposals.json"))
    ap.add_argument("--dry-run", action="store_true", help="don't write appearances back")
    args = ap.parse_args()

    if args.mode == "llm" and not args.backend:
        args.backend = "claude-code"

    data_dir = Path(args.data)
    entities = load_entities(data_dir)
    resolver = engine.Resolver(
        entities,
        load_yaml_list(data_dir / ".." / "detect" / "rejections.yaml"),
        load_yaml_list(data_dir / ".." / "detect" / "rules.yaml"),
    )

    slugs = args.masechet or sorted(p.stem for p in Path(args.masechot).glob("*.html")
                                    if p.stem != "index")

    mishnayot_out = []          # ordered review surface
    proposals = {}              # norm -> proposal (new entities, grouped)
    ambiguous = []
    appends = {}                # slug -> set(ref)  (known appearances to write)
    counts = {"mishnayot": 0, "known": 0, "new": 0, "ambiguous": 0, "suppressed": 0}

    if args.mode == "llm":
        detector = detect_llm(args.masechot, slugs, args.backend,
                              args.model, args.base_url)
    else:
        detector = detect_bold(args.masechot, slugs)

    for ref, mentions in detector:
        counts["mishnayot"] += 1
        detected = []
        for form, kind in mentions:
            res = resolver.resolve(form, kind, ref)
            row = {"form": form, "kind": kind, "status": res["status"]}
            if res["status"] == "known":
                row["slug"] = res["slug"]
                appends.setdefault(res["slug"], set()).add(ref)
                counts["known"] += 1
            elif res["status"] == "rejected":
                counts["suppressed"] += 1
            elif res["status"] == "ambiguous":
                row["candidates"] = res["candidates"]
                ambiguous.append({"ref": ref, "form": form, "kind": kind,
                                  "candidates": res["candidates"]})
                counts["ambiguous"] += 1
            else:  # new — group as a proposal; later occurrences accrue refs
                norm = res["norm"]
                row["proposal"] = norm
                p = proposals.setdefault(norm, {"kind": kind, "forms": [], "refs": [],
                                                "suggested_slug": None})
                if form not in p["forms"]:
                    p["forms"].append(form)
                if ref not in p["refs"]:
                    p["refs"].append(ref)
                counts["new"] += 1
            detected.append(row)
        mishnayot_out.append({"ref": ref, "detected": detected})

    # count distinct new entities, not occurrences
    counts["new"] = len(proposals)
    out = {
        "run": {"mode": args.mode, "counts": counts},
        "mishnayot": mishnayot_out,
        "proposals": proposals,
        "ambiguous": ambiguous,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # write known appearances back to the entity YAML (idempotent)
    written = 0
    if not args.dry_run:
        by_slug = {e["slug"]: e for e in entities}
        for slug, refs in appends.items():
            e = by_slug[slug]
            changed = False
            for ref in sorted(refs):
                if kb.add_appearance(e["doc"], "mishnah", ref):
                    changed = True
            if changed:
                kb.save_entity(e["path"], e["doc"])
                written += 1

    print(f"proposals -> {out_path}")
    print(f"  {counts}")
    print(f"  {'(dry-run) ' if args.dry_run else ''}entities gaining appearances: {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
