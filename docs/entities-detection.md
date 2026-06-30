# Mishnah Entity Detection — Identity / Review / Enhance

**Status:** v0 (foundational). How the entities knowledge base is *populated* from the corpus: a re-runnable detection pass that proposes entities and appearances, a human review step that promotes/rejects, and an enhancement layer that decorates what survives. The store itself is specified in [`entities-knowledge-base.md`](entities-knowledge-base.md); the rendered views in [`entities-display.md`](entities-display.md).

## The shape of it

Detection is a **one-time job over a closed corpus** — but the *extractor* is re-run many times as prompts/models/commentaries are tuned. So the design optimizes for **cheap re-review, not cheap re-runs**: each pass should only resurface what's genuinely new.

```
identity   kb-detect.py   walk mishna-by-mishna -> appearances + proposals (the delta)
review     review SPA + kb-promote.py   triage proposals -> entities / rejections / rules
enhance    importers + perushim + manual   decorate the promoted entities (forever)
```

The loop runs `detect → review → promote → detect …`. Promoted entities resolve silently on the next run, rejected forms stay suppressed, and rules auto-disambiguate — so a re-run after a prompt tweak shows only what *this* prompt newly found.

## Re-run memory (why delta-review works)

Two kinds of memory, and you mostly already have one:

- **Positive = the entity files themselves.** Once you accept "חיטה → `chitah`", that entity's own `variants` are the lexicon; any later mention matching its forms auto-resolves to an appearance. The KB is its own resolved dictionary.
- **Negative = `entities/detect/rejections.yaml`.** Forms marked "not an entity", so re-runs suppress them instead of re-asking. Per-mishna by default, with a global escape hatch.

Ambiguity (a form matching >1 entity) is handled by **`entities/detect/rules.yaml`** — most-specific scope wins (`mishna` > `masechet` > `global`).

## Resolution (per detected mention)

`kb_detect.Resolver.resolve(form, kind, ref)` returns one of:

1. **rejected** — matches a rejection in scope (`global`, or `mishna` for this `ref`) → suppressed.
2. **known** — normalized form (with single-prefix tolerance, e.g. `הַחִטִּים`→`חטים`) matches exactly one entity of that kind → append `{ref}` to its appearances (`source: detector`, idempotent), silently.
3. **ambiguous** — matches >1 entity → a rule resolves it if one applies, else it's queued.
4. **new** — matches nothing → a proposal, grouped by normalized form; refs accrue across the run.

Appearances are never pre-listed; they accrue as the walk proceeds. Accept a new entity once at its first occurrence and every later occurrence is "known" and just appends.

## Files

```
entities/
  detect/
    proposals.json     # generated each run; the review surface (gitignored)
    decisions.json     # exported by the SPA; consumed by kb-promote (gitignored)
    rejections.yaml    # durable negative memory (committed; schema-validated)
    rules.yaml         # durable disambiguation rules (committed; schema-validated)
  review/index.html    # the review SPA (static, no server)
  schema/
    rejection.schema.json  rule.schema.json
scripts/
  kb_detect.py         # the pure resolution engine (importable)
  kb-detect.py         # identity CLI: --mode bold (offline) | --mode llm (your machine)
  kb-promote.py        # review CLI: apply decisions.json
```

## `proposals.json` (generated; SPA loads it)

Mishna-ordered detections, plus new entities grouped so you promote once:

```jsonc
{
  "run": { "mode": "bold", "counts": { "mishnayot": 94, "known": 4, "new": 89, "ambiguous": 0, "suppressed": 0 } },
  "mishnayot": [
    { "ref": "makkot 1:10", "detected": [
        { "form": "רַבִּי עֲקִיבָא", "kind": "person", "status": "known", "slug": "akiva" },
        { "form": "רַבִּי טַרְפוֹן", "kind": "person", "status": "new", "proposal": "רבי טרפון" } ] }
  ],
  "proposals": {
    "רבי טרפון": { "kind": "person", "forms": ["רַבִּי טַרְפוֹן"], "refs": ["makkot 1:10"], "suggested_slug": null }
  },
  "ambiguous": [ { "ref": "...", "form": "רבי יהודה", "kind": "person", "candidates": ["yehuda-b-ilai", "yehuda-ha-nasi"] } ]
}
```

## `decisions.json` (SPA exports; `kb-promote` applies)

```jsonc
{
  "accept": [ { "kind": "person", "slug": "tarfon", "type": "tanna",
                "names": { "he": "רבי טרפון", "en": "Rabbi Tarfon" },
                "variants": ["רַבִּי טַרְפוֹן"], "refs": ["makkot 1:10"] } ],
  "reject": [ { "form": "זה הכלל", "kind": "plant", "scope": "global" } ],
  "rules":  [ { "form": "רבי יהודה", "kind": "person", "resolve": "yehuda-b-ilai", "scope": "global" } ]
}
```
`accept` → an entity stub (`status: stub`) with its variants and accrued appearances. `reject` → appended to `rejections.yaml`. `rules` → appended to `rules.yaml`.

## The review SPA

`entities/review/index.html` is a static page (no server): load a `proposals.json`, triage new entities (slug / type / English, then **accept** or **reject globally**) and ambiguous forms (pick a slug + scope → **a rule**), and **Export decisions.json**. Hand-writing `decisions.json` works too.

## Detection modes

- **`--mode bold` (deterministic, offline).** Harvests the rabbinic names the house style already **bolds** in `masechot/` — a high-precision, free people signal. This is the recommended first pass and the one runnable in CI.
- **`--mode llm` (your machine).** Reads each mishna — optionally with linked **perushim** (Bartenura, Rambam…) as context for disambiguation and discovery — and lists people/places/plants. Reuses `format.py`'s backend abstraction; needs network + an API key, so it runs on your machine, like the live importers. *(Not implemented in the sandboxed build.)*

Both modes feed the same `Resolver` and emit the same `proposals.json`; combine them (bold as a precision cross-check on the LLM's people).

## What runs where

Everything except the LLM sweep is offline and tested: the resolution engine, `--mode bold` detection over the real masechot, `kb-promote`, the rejection/rule schemas (wired into `kb-validate`), and the SPA. The LLM sweep inside `kb-detect --mode llm` is the single piece you run off-sandbox.
