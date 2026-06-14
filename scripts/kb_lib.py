"""Shared library for the entities knowledge base: round-trip YAML I/O and the
§8 merge rules. Importers (kb-import-*.py) are thin wrappers — fetch, transform,
then call these upserts.

Every write obeys docs/entities-knowledge-base.md §8:
  - additive, idempotent upserts: re-running an import produces zero churn
  - NEVER auto-overwrite a `confirmed: true` claim — conflicts go to a review
    queue (entities/conflicts.log), never the field
  - appearances dedupe by ref
  - single-valued fields: at most one claim per source (updatable in place)
  - multi-valued fields (coordinates, candidates): append per (value, source)

Round-trip YAML (ruamel) preserves comments and adjudication notes on write.

Requires: ruamel.yaml.
"""

from datetime import date as _date
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

KIND_DIR = {"person": "people", "place": "places", "plant": "plants"}
DIR_KIND = {v: k for k, v in KIND_DIR.items()}
# canonical key order when a claim is first written
_CLAIM_ORDER = ["value", "source", "confidence", "asserted_by", "date", "confirmed", "note"]


def make_yaml():
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096  # don't wrap long Hebrew/URLs
    y.indent(mapping=2, sequence=2, offset=0)
    return y


def today():
    return _date.today().isoformat()


def load_entity(path):
    with open(path, encoding="utf-8") as f:
        return make_yaml().load(f)


def save_entity(path, data):
    with open(path, "w", encoding="utf-8") as f:
        make_yaml().dump(data, f)


def entity_path(data_dir, kind, slug):
    """kind may be singular ('person') or a folder ('people')."""
    folder = KIND_DIR.get(kind, kind)
    return Path(data_dir) / folder / f"{slug}.yaml"


def flow_map(d):
    """A small mapping rendered inline (`{a: 1, b: 2}`) to match the hand-written
    style of coordinate and taxon values."""
    m = CommentedMap(d)
    m.fa.set_flow_style()
    return m


def _plain(x):
    """Strip ruamel wrappers so values compare by content."""
    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_plain(v) for v in x]
    return x


def _ensure_path_list(data, field):
    """Navigate a dotted path, creating intermediate maps, and return the list
    at the leaf (creating it if absent)."""
    parts = field.split(".")
    node = data
    for p in parts[:-1]:
        if node.get(p) is None:
            node[p] = CommentedMap()
        node = node[p]
    last = parts[-1]
    if node.get(last) is None:
        node[last] = CommentedSeq()
    return node[last]


def _make_claim(value, source, confidence, asserted_by, date, note, confirmed, extra):
    c = CommentedMap()
    c["value"] = value
    c["source"] = source
    if confidence is not None:
        c["confidence"] = confidence
    if asserted_by is not None:
        c["asserted_by"] = asserted_by
    if date is not None:
        c["date"] = date
    for k, v in (extra or {}).items():
        c[k] = v
    c["confirmed"] = bool(confirmed)
    if note is not None:
        c["note"] = note
    return c


def upsert_claim(data, field, value, source, *, mode, conflicts, entity_slug="",
                 confidence=None, asserted_by=None, date=None, note=None,
                 confirmed=False, extra=None):
    """Upsert a claim into the list at `field`. Returns one of
    'unchanged' | 'added' | 'updated' | 'conflict'.

    mode='multi': append iff (value, source) is new; never overwrites.
    mode='single': at most one claim per source. Same value -> no-op.
        Different value -> update in place, UNLESS the existing claim is
        confirmed, in which case record a conflict and leave it untouched.
    """
    lst = _ensure_path_list(data, field)
    pv = _plain(value)

    if mode == "multi":
        for c in lst:
            if c.get("source") == source and _plain(c.get("value")) == pv:
                return "unchanged"
        lst.append(_make_claim(value, source, confidence, asserted_by, date,
                               note, confirmed, extra))
        return "added"

    if mode == "single":
        for c in lst:
            if c.get("source") != source:
                continue
            if _plain(c.get("value")) == pv:
                return "unchanged"
            if c.get("confirmed"):
                conflicts.append({
                    "entity": entity_slug, "field": field, "source": source,
                    "kept": _plain(c.get("value")), "rejected": pv,
                })
                return "conflict"
            c["value"] = value
            if confidence is not None:
                c["confidence"] = confidence
            if date is not None:
                c["date"] = date
            return "updated"
        lst.append(_make_claim(value, source, confidence, asserted_by, date,
                               note, confirmed, extra))
        return "added"

    raise ValueError(f"unknown mode: {mode}")


def add_appearance(data, work, ref):
    """Append a mishnah/other appearance ref, deduped. Returns True if added."""
    lst = _ensure_path_list(data, f"appearances.{work}")
    if ref in lst:
        return False
    lst.append(ref)
    return True


def set_external_id(data, authority, value):
    """Set an external id (not a claim — no confirmed-protection). Idempotent."""
    if data.get("ids") is None:
        data["ids"] = CommentedMap()
    if data["ids"].get(authority) == value:
        return False
    data["ids"][authority] = value
    return True


def merge_variants(data, field, values):
    """Add string variants to the list at `field`, deduped, order-preserving.
    Returns the count added."""
    lst = _ensure_path_list(data, field)
    added = 0
    for v in values:
        if v not in lst:
            lst.append(v)
            added += 1
    return added


def write_conflicts(conflicts, path):
    """Append conflict records to the review queue (gitignored)."""
    if not conflicts:
        return
    with open(path, "a", encoding="utf-8") as f:
        for c in conflicts:
            f.write(
                f"{today()}\t{c['entity']}\t{c['field']}\tsource={c['source']}\t"
                f"kept={c['kept']!r}\trejected={c['rejected']!r}\n"
            )
