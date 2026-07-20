"""Pipeline control endpoints: trigger steps, get status."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..config import DATA_DIR, DETECT_DIR, ENTITIES_DIR, MASECHOT_DIR, SCRIPTS_DIR
from ..models import (BuildResult, DetectRequest, EnrichRequest, EnrichResult,
                       EntityCounts, JobStatus, PipelineStatus, PromoteRequest,
                       PromoteResult, RenderResult, ValidateResult)

router = APIRouter()

# In-memory job tracking (single-user, no persistence needed)
_jobs: dict[str, dict] = {}


def _entity_counts() -> EntityCounts:
    counts = EntityCounts()
    for kind in ("people", "places", "plants"):
        d = DATA_DIR / kind
        if d.exists():
            setattr(counts, kind, len(list(d.glob("*.yaml"))))
    return counts


def _last_modified(path: Path) -> str | None:
    if path.exists():
        return datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        ).isoformat()
    return None


@router.get("/status")
def pipeline_status() -> PipelineStatus:
    from ..models import (DecisionsStatus, DetectStatus, KnowledgeDbStatus,
                          SiteStatus, ValidationStatus)

    # Detect
    proposal_files = [f.name for f in sorted(DETECT_DIR.glob("proposals*.json"))]
    detect_mtime = None
    if proposal_files:
        latest = max(
            (DETECT_DIR / f).stat().st_mtime
            for f in proposal_files
            if (DETECT_DIR / f).exists()
        )
        detect_mtime = datetime.fromtimestamp(latest, tz=timezone.utc).isoformat()

    # Decisions
    decision_files = [f.name for f in sorted(DETECT_DIR.glob("decisions*.json"))]
    dec_mtime = None
    if decision_files:
        latest = max(
            (DETECT_DIR / f).stat().st_mtime
            for f in decision_files
            if (DETECT_DIR / f).exists()
        )
        dec_mtime = datetime.fromtimestamp(latest, tz=timezone.utc).isoformat()

    # Knowledge DB
    db_path = ENTITIES_DIR / "knowledge.db"

    # Site
    site_dir = ENTITIES_DIR / "site"
    page_count = len(list(site_dir.glob("**/*.html"))) if site_dir.exists() else 0

    return PipelineStatus(
        detect=DetectStatus(proposal_files=proposal_files, last_modified=detect_mtime),
        decisions=DecisionsStatus(files=decision_files, last_modified=dec_mtime),
        entities=_entity_counts(),
        knowledge_db=KnowledgeDbStatus(
            exists=db_path.exists(),
            last_modified=_last_modified(db_path),
        ),
        site=SiteStatus(exists=site_dir.exists(), page_count=page_count),
        validation=ValidationStatus(),
    )


# --- Detect (long-running, async) ---

@router.post("/detect")
async def start_detect(req: DetectRequest) -> dict:
    job_id = str(uuid.uuid4())[:8]

    cmd = ["python3", str(SCRIPTS_DIR / "kb-detect.py"), "--mode", req.mode]
    if req.masechet:
        cmd += ["--masechet", req.masechet]
    if req.backend:
        cmd += ["--backend", req.backend]
    if req.dry_run:
        cmd.append("--dry-run")

    _jobs[job_id] = {"status": "running", "progress": [], "result": None}
    asyncio.create_task(_run_detect(job_id, cmd))
    return {"job_id": job_id}


async def _run_detect(job_id: str, cmd: list[str]):
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            _jobs[job_id]["progress"].append(text)

        await proc.wait()
        _jobs[job_id]["status"] = "done" if proc.returncode == 0 else "error"
        _jobs[job_id]["result"] = {"returncode": proc.returncode}
    except Exception as e:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["result"] = {"error": str(e)}


@router.get("/detect/{job_id}")
def detect_status(job_id: str) -> JobStatus:
    if job_id not in _jobs:
        raise HTTPException(404, f"Job not found: {job_id}")
    j = _jobs[job_id]
    return JobStatus(
        status=j["status"],
        progress=j["progress"][-20:],  # last 20 lines
        result=j["result"],
    )


# --- Promote ---

@router.post("/promote")
def promote(req: PromoteRequest) -> PromoteResult:
    path = DETECT_DIR / f"decisions-{req.source}.json"
    if not path.exists():
        raise HTTPException(404, f"Decisions not found: {req.source}")

    data = json.loads(path.read_text(encoding="utf-8"))

    # Convert dict format to list if needed (PATCH saves as dict)
    accept = list(data.get("accept", {}).values()) if isinstance(data.get("accept"), dict) else data.get("accept", [])
    reject = list(data.get("reject", {}).values()) if isinstance(data.get("reject"), dict) else data.get("reject", [])
    rules = list(data.get("rules", {}).values()) if isinstance(data.get("rules"), dict) else data.get("rules", [])

    import importlib.util
    spec = importlib.util.spec_from_file_location("kb_promote", SCRIPTS_DIR / "kb-promote.py")
    kb_promote = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kb_promote)

    created = []
    skipped = []
    for d in accept:
        slug = d.get("slug", "")
        kind = d.get("kind", "person")
        folder = {"person": "people", "place": "places", "plant": "plants"}.get(kind, "people")
        out_path = DATA_DIR / folder / f"{slug}.yaml"
        if out_path.exists():
            skipped.append(slug)
            continue
        stub = kb_promote.build_stub(d)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        kb_promote.write_stub(out_path, stub)
        created.append(slug)

    # Rejections
    rej_path = DETECT_DIR / "rejections.yaml"
    rej_added = 0
    if reject:
        import yaml
        existing = yaml.safe_load(rej_path.read_text(encoding="utf-8")) if rej_path.exists() else []
        existing = existing or []
        for r in reject:
            if not any(e.get("form") == r.get("form") and e.get("kind") == r.get("kind") for e in existing):
                existing.append(r)
                rej_added += 1
        rej_path.write_text(yaml.dump(existing, allow_unicode=True, default_flow_style=False), encoding="utf-8")

    # Rules
    rules_path = DETECT_DIR / "rules.yaml"
    rules_added = 0
    if rules:
        import yaml
        existing = yaml.safe_load(rules_path.read_text(encoding="utf-8")) if rules_path.exists() else []
        existing = existing or []
        for r in rules:
            if not any(e.get("form") == r.get("form") and e.get("resolve") == r.get("resolve") for e in existing):
                existing.append(r)
                rules_added += 1
        rules_path.write_text(yaml.dump(existing, allow_unicode=True, default_flow_style=False), encoding="utf-8")

    return PromoteResult(created=created, skipped=skipped,
                         rejections_added=rej_added, rules_added=rules_added)


# --- Build ---

@router.post("/build")
def build() -> BuildResult:
    import importlib.util
    spec = importlib.util.spec_from_file_location("kb_build", SCRIPTS_DIR / "kb-build.py")
    kb_build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kb_build)

    out_path = ENTITIES_DIR / "knowledge.db"
    counts = kb_build.build(str(DATA_DIR), str(out_path))
    return BuildResult(path=str(out_path), counts=counts or {})


# --- Render (subprocess) ---

@router.post("/render")
async def render() -> RenderResult:
    proc = await asyncio.create_subprocess_exec(
        "python3", str(SCRIPTS_DIR / "kb-render.py"),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    output = stdout.decode("utf-8", errors="replace")

    # Parse page count from output
    import re
    m = re.search(r"(\d+)\s*pages?", output)
    page_count = int(m.group(1)) if m else 0

    site_dir = ENTITIES_DIR / "site"
    if site_dir.exists():
        page_count = max(page_count, len(list(site_dir.glob("**/*.html"))))

    return RenderResult(pages_written=page_count, path=str(site_dir))


# --- Enrich (subprocess) ---

@router.post("/enrich")
async def enrich(req: EnrichRequest) -> EnrichResult:
    cmd = ["python3", str(SCRIPTS_DIR / "kb-enrich.py")]
    if req.masechet:
        cmd += ["--masechet", req.masechet]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    output = stdout.decode("utf-8", errors="replace")

    import re
    pages = 0
    m = re.search(r"(\d+)\s*pages?", output)
    if m:
        pages = int(m.group(1))

    marks = {}
    for kind in ("person", "place", "plant"):
        m = re.search(rf"{kind}\w*:\s*(\d+)", output, re.I)
        if m:
            marks[kind] = int(m.group(1))

    return EnrichResult(pages=pages, marks=marks)


# --- Validate (subprocess) ---

@router.post("/validate")
async def validate() -> ValidateResult:
    proc = await asyncio.create_subprocess_exec(
        "python3", str(SCRIPTS_DIR / "kb-validate.py"),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    output = stdout.decode("utf-8", errors="replace")

    passed = proc.returncode == 0
    import re
    ok = len(re.findall(r"✓|OK|passed", output))
    bad = len(re.findall(r"✗|FAIL|error", output, re.I))

    return ValidateResult(passed=passed, files_ok=ok, files_bad=bad, errors=[])
