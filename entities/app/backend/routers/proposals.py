"""Proposals and decisions endpoints."""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..config import DETECT_DIR
from ..models import DecisionsFile, PatchDecision, ProposalSummary

router = APIRouter()


@router.get("/")
def list_proposals() -> list[ProposalSummary]:
    """List all proposal files."""
    files = sorted(DETECT_DIR.glob("proposals-*.json"))
    # Also check for proposals.json (multi-masechet)
    unified = DETECT_DIR / "proposals.json"
    if unified.exists():
        files.append(unified)

    out = []
    for f in files:
        slug = f.stem.replace("proposals-", "").replace("proposals", "all")
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            run = data.get("run", {})
            out.append(ProposalSummary(
                slug=slug,
                mode=run.get("mode"),
                counts=run.get("counts", {}),
                modified=datetime.fromtimestamp(
                    f.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            ))
        except (json.JSONDecodeError, OSError):
            out.append(ProposalSummary(slug=slug))
    return out


@router.get("/{slug}")
def get_proposals(slug: str):
    """Load proposals for a masechet."""
    if slug == "all":
        path = DETECT_DIR / "proposals.json"
    else:
        path = DETECT_DIR / f"proposals-{slug}.json"
    if not path.exists():
        raise HTTPException(404, f"Proposals not found: {slug}")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/decisions/{slug}")
def get_decisions(slug: str) -> DecisionsFile:
    """Load saved decisions for a masechet."""
    path = DETECT_DIR / f"decisions-{slug}.json"
    if not path.exists():
        return DecisionsFile()
    data = json.loads(path.read_text(encoding="utf-8"))
    return DecisionsFile(**data)


@router.put("/decisions/{slug}")
def save_decisions(slug: str, decisions: DecisionsFile):
    """Save full decisions file."""
    path = DETECT_DIR / f"decisions-{slug}.json"
    DETECT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(decisions.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"saved": True, "path": str(path)}


@router.patch("/decisions/{slug}")
def patch_decision(slug: str, patch: PatchDecision):
    """Update a single decision (incremental save)."""
    path = DETECT_DIR / f"decisions-{slug}.json"
    DETECT_DIR.mkdir(parents=True, exist_ok=True)

    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"accept": {}, "reject": {}, "rules": {}}

    # Internally keyed by norm for idempotent toggling
    # Convert list format to dict if needed
    for key in ("accept", "reject", "rules"):
        if isinstance(data.get(key), list):
            if key == "accept":
                data[key] = {d.get("slug", ""): d for d in data[key]}
            else:
                data[key] = {d.get("form", ""): d for d in data[key]}

    norm = patch.norm
    if patch.action == "accept":
        data.setdefault("accept", {})[norm] = patch.data
        data.get("reject", {}).pop(norm, None)
    elif patch.action == "reject":
        data.setdefault("reject", {})[norm] = patch.data
        data.get("accept", {}).pop(norm, None)
    elif patch.action == "rule":
        data.setdefault("rules", {})[norm] = patch.data
    elif patch.action == "undo":
        data.get("accept", {}).pop(norm, None)
        data.get("reject", {}).pop(norm, None)
        data.get("rules", {}).pop(norm, None)

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"updated": True}
