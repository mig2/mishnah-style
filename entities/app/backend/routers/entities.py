"""Entity browsing and search endpoints."""

import json
import re
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from ..config import DATA_DIR, DETECT_DIR, MASECHOT_DIR

router = APIRouter()

KINDS = {"people": "person", "places": "place", "plants": "plant"}


def _strip_nikkud(text: str) -> str:
    return re.sub(r"[\u0591-\u05C7]", "", text)


@router.get("/")
def list_entities(kind: str | None = None, search: str | None = None):
    """Browse/search entities."""
    out = []
    folders = [kind] if kind and kind in KINDS.values() else list(KINDS.keys())
    folder_map = {v: k for k, v in KINDS.items()}

    for folder_name in folders:
        if folder_name in KINDS:
            entity_kind = KINDS[folder_name]
            folder = DATA_DIR / folder_name
        else:
            entity_kind = folder_name
            folder = DATA_DIR / folder_map.get(folder_name, folder_name)

        if not folder.exists():
            continue

        for path in sorted(folder.glob("*.yaml")):
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not doc:
                continue

            # Extract display info
            if entity_kind == "plant":
                term = doc.get("term", {}) or {}
                he = term.get("he", "")
                en = term.get("en_common", "")
                entity_type = doc.get("type", "")
            else:
                names = doc.get("names", {}) or {}
                he = names.get("he", "")
                en = names.get("en", "")
                entity_type = doc.get("type", "")

            # Search filter
            if search:
                search_lower = search.lower()
                search_stripped = _strip_nikkud(search)
                haystack = f"{he} {en} {path.stem}".lower()
                haystack_stripped = _strip_nikkud(haystack)
                if search_lower not in haystack and search_stripped not in haystack_stripped:
                    continue

            appearances = doc.get("appearances", []) or []
            out.append({
                "slug": path.stem,
                "kind": entity_kind,
                "he": he,
                "en": en,
                "type": entity_type,
                "appearance_count": len(appearances),
            })

    return out


@router.get("/rejections")
def list_rejections():
    """List all rejections."""
    path = DETECT_DIR / "rejections.yaml"
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8")) or []


@router.get("/rules")
def list_rules():
    """List all disambiguation rules."""
    path = DETECT_DIR / "rules.yaml"
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8")) or []


@router.get("/{kind}/{slug}")
def get_entity(kind: str, slug: str):
    """Get full entity detail."""
    folder_map = {"person": "people", "place": "places", "plant": "plants"}
    folder = folder_map.get(kind)
    if not folder:
        raise HTTPException(400, f"Unknown kind: {kind}")
    path = DATA_DIR / folder / f"{slug}.yaml"
    if not path.exists():
        raise HTTPException(404, f"Entity not found: {kind}/{slug}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@router.get("/masechot")
def list_masechot():
    """List available masechot."""
    return sorted([
        {"slug": p.stem}
        for p in MASECHOT_DIR.glob("*.html")
        if p.stem != "index"
    ], key=lambda x: x["slug"])
