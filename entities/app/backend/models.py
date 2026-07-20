"""Pydantic models for the entities pipeline API."""

from pydantic import BaseModel


# --- Pipeline status ---

class DetectStatus(BaseModel):
    proposal_files: list[str] = []
    last_modified: str | None = None


class DecisionsStatus(BaseModel):
    files: list[str] = []
    last_modified: str | None = None


class EntityCounts(BaseModel):
    people: int = 0
    places: int = 0
    plants: int = 0


class KnowledgeDbStatus(BaseModel):
    exists: bool = False
    last_modified: str | None = None


class SiteStatus(BaseModel):
    exists: bool = False
    page_count: int = 0


class ValidationStatus(BaseModel):
    last_run: str | None = None
    passed: bool | None = None


class PipelineStatus(BaseModel):
    detect: DetectStatus = DetectStatus()
    decisions: DecisionsStatus = DecisionsStatus()
    entities: EntityCounts = EntityCounts()
    knowledge_db: KnowledgeDbStatus = KnowledgeDbStatus()
    site: SiteStatus = SiteStatus()
    validation: ValidationStatus = ValidationStatus()


# --- Detect ---

class DetectRequest(BaseModel):
    mode: str = "bold"
    masechet: str | None = None
    backend: str | None = None
    dry_run: bool = False


class JobStatus(BaseModel):
    status: str  # running | done | error
    progress: list[str] = []
    result: dict | None = None


# --- Proposals ---

class ProposalSummary(BaseModel):
    slug: str
    mode: str | None = None
    counts: dict = {}
    modified: str | None = None


# --- Decisions ---

class AcceptDecision(BaseModel):
    kind: str
    slug: str
    variants: list[str] = []
    refs: list[str] = []
    type: str | None = None
    term_type: str | None = None
    names: dict | None = None
    term: dict | None = None


class RejectDecision(BaseModel):
    form: str
    kind: str
    scope: str = "global"
    ref: str | None = None


class RuleDecision(BaseModel):
    form: str
    kind: str
    resolve: str
    scope: str = "global"
    masechet: str | None = None
    ref: str | None = None


class DecisionsFile(BaseModel):
    accept: list[AcceptDecision] = []
    reject: list[RejectDecision] = []
    rules: list[RuleDecision] = []


class PatchDecision(BaseModel):
    action: str  # accept | reject | rule
    norm: str  # the normalized form key
    data: dict


# --- Pipeline results ---

class PromoteRequest(BaseModel):
    source: str  # slug name, e.g. "brachot"


class PromoteResult(BaseModel):
    created: list[str] = []
    skipped: list[str] = []
    rejections_added: int = 0
    rules_added: int = 0


class BuildResult(BaseModel):
    path: str = ""
    counts: dict = {}


class RenderResult(BaseModel):
    pages_written: int = 0
    path: str = ""


class EnrichRequest(BaseModel):
    masechet: str | None = None


class EnrichResult(BaseModel):
    pages: int = 0
    marks: dict = {}


class ValidateResult(BaseModel):
    passed: bool = False
    files_ok: int = 0
    files_bad: int = 0
    errors: list[dict] = []
