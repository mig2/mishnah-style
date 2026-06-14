# Mishnah Entities Knowledge Base — Database Spec

**Status:** v0 (foundational). This spec defines *the database* — the accumulating store of people, places, and plants found in the Mishnah. It does **not** cover the detection pipeline; the detector is a later, separate writer into this store (see §10).

This is a companion subsystem to the text-formatting pipeline that produces `masechot/`. It is adapted to this repo's existing conventions: the slug rules already used for masechet filenames, the deep-link anchor scheme in [`docs/html-format.md`](html-format.md), the practice of gitignoring derived artifacts, and a flat `scripts/` directory. Where this spec departs from a generic "fresh repo" layout, it is to match those conventions; the departures are called out inline.

-----

## 1. What this is, and what it is not

This is a **knowledge base that accumulates**, not a stateless pipeline. Records are long-lived, enriched from many sources over time, and repeatedly corrected by hand. Design priorities follow from that — not throughput (the corpus is tiny: a few hundred people, a few hundred places, ~150–300 plant terms), but:

1. **Stable identity** — an entity keeps its key across re-imports and re-identifications.
2. **Provenance** — every fact knows where it came from and when.
3. **Idempotent, mergeable updates** — re-running an import causes no churn and no duplicates.
4. **Protected curation** — automated refreshes never clobber human-confirmed facts.
5. **Native support for contested, multi-valued facts** — especially plant identifications and disputed place coordinates.

The first goal is this store, standing alone. Mishnah integration comes later.

-----

## 2. Architecture: git-tracked YAML as source of truth, derived SQLite as index

- **Source of truth:** one human-readable **YAML file per entity**, committed to git.
- **Query index:** a **SQLite** database compiled from the YAML by a deterministic build step.
- The SQLite is **disposable and regenerable**. Never hand-edit it. Rebuild from YAML.

Why this shape fits an accumulating, human-in-the-loop KB:

- **Git history is the audit log.** Each discovery is a commit; `git blame` on a field shows when and why it changed — provenance-over-time for free.
- **Diffs are reviewable and merge-friendly.** A discovery touches one file; clean diffs, minimal conflicts; an agent can make targeted edits without rewriting a monolith.
- **Hand- and agent-editable**, with adjudication notes living next to the data.
- **You still get SQL** for the eventual map and cross-entity queries by rebuilding the index.

This is the same shape as the text pipeline already in this repo: a deterministic build from a public-domain source, with the database a *derived artifact*. There, `download.py → format.py → … → merge.py` turns Sefaria source text into `masechot/*.html`, and `verify.py` emits a derived HTML report. Here, `data/**/*.yaml` compiles into `knowledge.db`. In both cases the committed source is authoritative and the built artifact is regenerable (see §11 for how `knowledge.db` is gitignored, just like `sefaria/` and `output/`).

-----

## 3. Repository layout

The KB lives in its own top-level `entities/` directory — paralleling `masechot/`, which holds everything for the text subsystem — so the two subsystems stay cleanly separated. Its build and validation scripts live in the shared `scripts/` directory, alongside the existing pipeline scripts, so all tooling is discoverable in one place (as documented in the README).

```
entities/
  data/
    people/     akiva.yaml  yehuda-b-ilai.yaml  …     # one file per entity, filename == slug
    places/     tzippori.yaml  yavne.yaml  …
    plants/     chitah.yaml  ezov.yaml  …
    sources.yaml                                       # source registry (§6)
    vocab/                                             # controlled vocabularies
      generations.yaml  sedarim.yaml  halachic-categories.yaml  regions.yaml
  schema/                                              # JSON Schema — the contract (§7, §9)
    claim.schema.json  person.schema.json  place.schema.json  plant.schema.json  source.schema.json
  knowledge.db        # derived; rebuildable. Gitignored (§11), like sefaria/ and output/.

scripts/
  kb-build.py         # compile entities/data/ -> entities/knowledge.db
  kb-validate.py      # validate every file against its schema
  kb-detect.py        # the detector (§10) — added later; one writer among several
```

Departures from a generic layout, and why:

- **`entities/` rather than a root `data/`** — keeps the KB self-contained and avoids ambiguity next to the text pipeline's working dirs (`sefaria/`, `output/`).
- **Build/validate scripts in `scripts/`, not a separate `build/`** — this repo keeps all tooling in a single flat `scripts/` directory (`download.py`, `format.py`, `verify.py`, `fix.py`, `merge.py`, `update-readme.py`). KB scripts follow suit, hyphen-prefixed `kb-` to group them.
- **A *scoped* `entities/CLAUDE.md`, not a root one** — durable invariants for coding agents belong in a `CLAUDE.md` (Claude Code reads nested `CLAUDE.md` files for the subtree they sit in), but scoped to `entities/` so they govern the KB without overriding the text-formatting repo at large. Its canonical text is the appendix at the end of this document, to be lifted into `entities/CLAUDE.md` when the subsystem is scaffolded. See §12 and the appendix.

-----

## 4. Identity: mint local IDs; external IDs are attributes

The **primary key is a locally-minted slug**, which is also the filename:

- `person:akiva`, `place:tzippori`, `plant:chitah` (the `type:` prefix is implied by the folder; the slug stored in-file is the bare `akiva`).

This is mandatory here because external authorities don't cover everything — especially plants, which have **no gazetteer**. You need a key that is stable *before* a Wikidata/Pleiades link is resolved, and that **survives an identification changing**. External identifiers are joinable *attributes*, never the primary key:

- people: `wikidata_qid`, `sefaria_slug`, `hyman_ref`, `bonayich_id`
- places: `wikidata_qid`, `pleiades_id`, `geonames_id`, `sefaria_slug`
- plants: `wikidata_qid`, `gbif_id`, `powo_id` (these live on each identification *candidate*, not the term)

**Slug rules** — identical to the convention already used for masechet filenames (`bava-kamma`, `rosh-hashanah`, `maaser-sheni`, `avodah-zarah`): lowercase ASCII, hyphen-separated, transliterated; disambiguate collisions with a patronymic or epithet (`yehuda-b-ilai` vs `yehuda-ha-nasi`). Slugs are permanent once minted — renames require an explicit alias, never a silent change. Masechet slugs referenced from entities (e.g. in `appearances`, §7) **must** match the existing `masechot/*.html` filenames exactly, so the two subsystems join cleanly.

-----

## 5. The claim model: contested facts are claims, not values

Any fact that can be disputed, sourced, or revised is stored as a **claim**, not a bare value. One shared shape, used by plant identification candidates, place coordinates, people identity resolution, biographical facts, and more:

```yaml
- value:        <the asserted value>          # scalar or object
  source:       <key into sources.yaml>        # provenance (required)
  confidence:   accepted | probable | minority | disputed | unknown
  asserted_by:  <scholar/authority, optional>  # e.g. Feliks, Löw
  date:         <ISO date the claim was recorded>
  confirmed:    false                          # true == human-ratified; protected (§8)
  note:         <free text, optional>          # adjudication reasoning
```

Rules:

- A field that holds claims holds a **list** of them. One may be marked as the **display/primary** value (`display_taxon` for plants, the chosen coordinate for places); the rest are retained dissent.
- A re-import **appends** a claim; it never overwrites an existing one.
- Simple, uncontestable facts (a Hebrew lemma, a tractate name) may be stored as plain scalars — don't over-model. Use claims where provenance or dispute is real.

**Status lifecycle** (per entity, top-level `status:`): `stub → enriched → reviewed → confirmed`.

- `stub` — minted, minimal (often just a name + one appearance).
- `enriched` — auto-populated from imports, unreviewed.
- `reviewed` — a human has looked at it.
- `confirmed` — human-ratified; the strongest protection applies.

-----

## 6. Source registry

Every source is a keyed entry in `entities/data/sources.yaml`. Provenance fields reference the **key** only.

```yaml
sefaria:
  citation: "Sefaria, sefaria.org"
  type: structured
  license: public-domain          # the Mishnah text itself is PD; same source the text pipeline uses
  trust_tier: 1                    # canonical reference/appearance source for this project
wikidata:
  citation: "Wikidata, wikidata.org"
  type: structured
  license: CC0
  trust_tier: 2
pleiades:
  citation: "Pleiades: A Gazetteer of Past Places, pleiades.stoa.org"
  type: structured
  license: CC-BY
  trust_tier: 1
low:
  citation: "Immanuel Löw, Die Flora der Juden, 4 vols., Vienna 1924–1934"
  type: scholarly-prose
  license: public-domain          # author d. 1944; pre-1929 vols PD, life+70 elapsed
  trust_tier: 1
feliks:
  citation: "Yehuda Feliks, works on flora of rabbinic literature"
  type: scholarly-prose
  license: in-copyright            # reference/adjudicate only — do NOT bulk-redistribute
  trust_tier: 1
detector:
  citation: "Mishnah entity detector (this project)"
  type: derived
  license: project
  trust_tier: 3
manual:
  citation: "Manual curation"
  type: human
  license: project
  trust_tier: 0                    # most trusted; lower number == higher trust
```

`sefaria` is a first-class source here because it is the canonical text source for the whole repo — the same source `download.py` fetches and `verify.py` checks against — and supplies the concordance behind `appearances.other` (§7).

Tracking `license` is not pedantry: it determines what may be redistributed if the dataset is ever published. The repo's posture is that **the underlying Mishnah text is public domain** while project-authored material is MIT (see the README); the KB extends that posture per-source. Löw (public domain) and Feliks (in copyright) differ sharply — Feliks is for adjudication and citation, not bulk extraction.

-----

## 7. Shared conventions

- **Appearances** are stored per entity as a deduped list of refs. The Mishnah refs use **this repo's canonical masechet slugs** (the `masechot/*.html` filenames), so each appearance resolves deterministically to a deep link via the anchor scheme in [`docs/html-format.md`](html-format.md):

  ```yaml
  appearances:
    mishnah: ["shekalim 4:2", "parah 11:7"]   # {masechet-slug} {chapter}:{mishna}; from the detector (later)
    other:   ["Tosefta Shekalim 2:1"]          # from the Sefaria concordance; free-form
  ```

  A `mishnah` ref of the form `{masechet-slug} {N}:{M}` maps to `masechot/{masechet-slug}.html#mishna-{N}-{M}` — e.g. `shekalim 4:2` → `masechot/shekalim.html#mishna-4-2`. Dedupe by normalized ref string. Adding an appearance is an idempotent upsert. (Refs into corpora this repo doesn't format — Tosefta, Bavli — stay free-form under `other:`.)
- **Computed fields are never stored raw.** `contemporaries` (people) and region rollups are derived at build time, not committed.
- All free text may be Hebrew or English; keep Hebrew in its own keyed subfields (`he`, `en`).

-----

## 8. Update & merge rules (the heart of an accumulating KB)

1. **Additive, idempotent upserts**, keyed on `(entity_id, source, field)`. Re-running the Wikidata import produces no duplicates and no diff.
2. **Appearances** dedupe by ref. **Identification candidates / coordinate candidates** append if the `(value, source)` pair is new, else no-op.
3. **Protected curation — the most important rule.** A field whose claim is `confirmed: true` is **never auto-overwritten**. If an automated refresh produces a conflicting value, it does **not** write — it records the conflict to a review queue (`entities/conflicts.log` or an `unreviewed_conflicts:` block on the entity) for a human to adjudicate.
4. **New entity → new file** (status `stub`). Never inline-create an entity inside another.
5. **Merges** (two slugs found to be one entity): keep the surviving slug, add the other to `aliases:`, move appearances and claims over, leave a tombstone file that redirects. Never delete history.

-----

## 9. Entity schemas

YAML files; validated against JSON Schema in `entities/schema/`. Below are the field models; the `*.schema.json` files are the enforceable contract and are the **first thing to scaffold**.

### 9.1 Person

```yaml
slug: akiva
status: enriched
type: tanna                 # tanna | amora | biblical | named-layperson | collective
aliases: []
names:
  he: "רבי עקיבא"
  en: "Rabbi Akiva"
  variants: ["רבי עקיבא בן יוסף", "ר' עקיבא"]
era:
  generation: 3             # tannaitic generation 1–6 — the reliable time unit
  floruit: "early 2nd c. CE"
  locale: ["bnei-brak"]     # slugs into places/
relationships:              # borrowed (Wikidata/biographical); typed edges
  teachers:  ["eliezer-b-hyrcanus", "yehoshua-b-hananiah"]
  students:  ["meir", "yehuda-b-ilai", "shimon-b-yochai"]
  family:    []
  # disputants / colleagues are DERIVED from the corpus at build time, not stored
bio:
  - value: "Leading tanna of the 3rd generation; foundational to the Mishnah."
    source: wikidata
    confidence: accepted
    confirmed: false
appearances:
  mishnah: []
  other: []
ids:
  wikidata_qid: Q310357
  sefaria_slug: rabbi-akiva
  hyman_ref: null
  bonayich_id: null
```

### 9.2 Place

```yaml
slug: tzippori
status: enriched
type: settlement            # settlement | region | temple_structure | water_feature | legal_domain
aliases: []
names:
  he: "ציפורי"
  en: "Tzippori"
  variants: ["צפורי"]
  classical: ["Sepphoris", "Diocaesarea"]   # Greco-Roman toponym; settlements only, often empty
  modern: { he: "ציפורי", ar: "صفورية", en: "Tzippori" }
geo:                        # null block for temple_structure & legal_domain
  coordinates:              # the displayed value; candidates retain dissent
    - value: { lat: 32.7522, lon: 35.2797 }
      source: pleiades
      confidence: accepted
      confirmed: false
  region: galilee
  modern_admin: "Israel, Northern District"
  consensus: identified     # identified | probable | disputed | unknown
media:
  photo: "https://commons.wikimedia.org/wiki/..."     # Wikidata P18
  map_link: "https://www.openstreetmap.org/?mlat=32.7522&mlon=35.2797"
plan: null                  # temple_structure only: { position, diagram_ref, source_ref }
appearances:
  mishnah: []
  other: []
ids:
  wikidata_qid: Q745966
  pleiades_id: "678378"
  geonames_id: null
  sefaria_slug: null
```

For `type: temple_structure`, `geo` is null and `plan` is populated:

```yaml
plan:
  position: "north of the altar"
  source_ref: "middot 3:1"                      # canonical masechet-slug ref (§7)
  diagram_ref: "mikdash-plan#lishkat-hagazit"   # internal schematic key, not lat/long
```

### 9.3 Plant

```yaml
slug: chitah
status: enriched
term:
  he: "חיטה"
  variants: ["חטה", "חטים", "חיטים"]    # spelling + plural + inflected
  en_common: "wheat"
term_type: species          # species | genus_or_group | folk_category | product | plant_part
identification:
  consensus: identified      # identified | contested | unknown
  display_taxon: "Triticum aestivum"
  candidates:
    - value: { taxon: "Triticum aestivum", rank: species }
      ids: { wikidata_qid: Q12100, gbif_id: null, powo_id: null }
      source: feliks
      asserted_by: Feliks
      confidence: accepted
      confirmed: false
    # a contested term carries >1 candidate, e.g. ezov:
    #   - value: { taxon: "Origanum syriacum", rank: species }  confidence: accepted
    #   - value: { taxon: "Satureja thymbra",  rank: species }  confidence: minority
names:                       # keyed to display_taxon; from botanical DBs
  botanical: "Triticum aestivum"
  family: "Poaceae"
  common_en: ["bread wheat", "wheat"]
  modern_he: ["חיטה"]
  arabic: ["قمح"]
usage:
  ethnobotanical: ["food"]
  medicinal:                 # historical/ethnobotanical, NOT medical guidance; provenance-tagged
    - value: "—"
      source: duke
      provenance: "Dr. Duke's Phytochemical & Ethnobotanical DB"
      confidence: probable
  halachic: ["kilayim", "maaser-dagan", "challah", "chadash"]   # DERIVED from the Mishnah
media:
  photo: "https://commons.wikimedia.org/wiki/..."          # of display_taxon
  illustration: "https://commons.wikimedia.org/wiki/...Köhler..."   # public-domain plate
appearances:
  mishnah: []
  other: []
ids: {}                      # term-level external ids rare; real ids live on candidates
```

`folk_category` terms (e.g. `kitnit`) carry a **set of member species** instead of a single `display_taxon`, and are excluded from the photo/map layer. `product` and `plant_part` terms are tagged and kept but likewise excluded from rendering.

-----

## 10. How the Mishnah detector slots in later

Designing this as a **multi-writer, provenance-tracked base** is exactly what makes the later bolt-on painless. When the detector is built (as `scripts/kb-detect.py`), it is just **one writer among several** (Wikidata import, Pleiades import, Löw/Feliks adjudication, manual curation, detector) — much as the text pipeline is a chain of small single-purpose scripts. It writes through the same upsert rules (§8) and does only two things:

1. emits **appearances** (`source: detector`) onto existing entities, using the canonical `{masechet-slug} {N}:{M}` ref form (§7), and
2. proposes **stub entities** (status `stub`) for unrecognized mentions, for human review.

It never overwrites identifications or biographical facts. Nothing about the detector needs to exist for the KB to be useful now. A natural input for it is the already-verified text in `masechot/` (or the Sefaria source the repo downloads), so detected refs line up exactly with the existing anchor scheme.

-----

## 11. Build & validation

- **Validation is the contract.** `scripts/kb-validate.py` validates every `entities/data/**/*.yaml` against its `entities/schema/*.schema.json`. Wire it into a pre-commit hook and CI; a file that doesn't validate doesn't land. Writing these schemas **is** the concrete first deliverable.
- **Build** (`scripts/kb-build.py`) compiles YAML → `entities/knowledge.db`. Suggested relational layout (flatten, don't mirror the nesting):
  - `entity(slug, type, status, he, en)`
  - `claim(entity_slug, field, value_json, source, confidence, confirmed, asserted_date, note)` — provenance-tracked fields land here
  - `appearance(entity_slug, ref, work, source)`
  - `external_id(entity_slug, authority, id)`
  - `source(key, citation, type, license, trust_tier)`
  - derive `contemporaries`, dispute/co-occurrence edges, and region rollups **at build time** into their own tables.
- The build is deterministic and idempotent: same YAML in → same DB out.
- **`entities/knowledge.db` is a derived artifact and is gitignored**, consistent with how this repo already treats built/working artifacts (`sefaria/`, `output/`, `__pycache__/` are all in `.gitignore`). Add `entities/knowledge.db` and `entities/conflicts.log` to `.gitignore`; never commit the DB. (This resolves the source spec's open question in favor of the repo's established convention: derived data is rebuilt, not committed.)

-----

## 12. First deliverables (in order)

1. **`entities/schema/claim.schema.json`** + **`source.schema.json`** — the shared spine.
2. **`entities/schema/{person,place,plant}.schema.json`** — the three contracts.
3. **`entities/data/sources.yaml`** + **`entities/data/vocab/*`** — registries and controlled vocabularies. The `sedarim`/masechet vocab reuses the existing `masechot/*.html` slugs verbatim, so appearance refs validate against the canonical list.
4. **`scripts/kb-validate.py`** + pre-commit/CI wiring, and the `.gitignore` entries from §11.
5. A handful of **hand-written exemplar entities** (one per type: `akiva`, `tzippori`, `chitah`) that validate — these double as fixtures and as living documentation, exactly as `exemplar-zevachim-1.html` does for the formatting skill.
6. **`scripts/kb-build.py`** producing `entities/knowledge.db`.
7. Only then: importers (Wikidata → people/places; Pleiades → places; Wikidata/Löw → plant candidates).

Format decision: **YAML for entity files** (hand-curation comfort, inline notes), **JSON Schema validating it**. Keep one entity per file.

Durable invariants for coding agents working in this subsystem are stated in the appendix below, whose canonical home is a scoped **`entities/CLAUDE.md`** created alongside deliverable 1 — scoped to the subtree so it governs the KB only, not the text-formatting repo at large. (Should the KB later grow interactive tooling, the same invariants can also seed a `.claude/skills/` skill, as the formatting rules do for the `mishnah` skill.)

-----

## Appendix: `entities/CLAUDE.md` — agent invariants

The canonical text of the scoped `entities/CLAUDE.md`. Create it with deliverable 1 (§12). These invariants are non-negotiable; honor them in every change to the KB subtree. Paths are written relative to `entities/` (e.g. `data/` = `entities/data/`).

> # CLAUDE.md — Mishnah Entities Knowledge Base
>
> This subsystem is an **accumulating knowledge base** of people, places, and plants in the Mishnah — not a stateless pipeline. Full design in [`docs/entities-knowledge-base.md`](entities-knowledge-base.md). The invariants below are non-negotiable; honor them in every change.
>
> ## Architecture
>
> - **Source of truth = one YAML file per entity, in git.** `knowledge.db` (SQLite) is a **derived, regenerable index** — never hand-edit it; rebuild from `data/`. It is gitignored.
> - Git history is the audit log. One discovery = one focused commit touching as few files as possible.
>
> ## Identity
>
> - **Primary key = a locally-minted slug** (= the filename). Slugs are permanent once minted; renames go through `aliases:`, never silent change. Masechet slugs referenced in `appearances` must match the repo's `masechot/*.html` filenames.
> - External IDs (`wikidata_qid`, `pleiades_id`, `powo_id`, …) are **joinable attributes, never the primary key**. An entity must be keyable before any external link is resolved.
>
> ## Facts & provenance
>
> - **Every contestable fact is a claim, not a bare value**: `{value, source, confidence, asserted_by, date, confirmed, note}`. Lists of claims; one may be the display value, the rest retained dissent.
> - **Every claim cites a `source`** that exists in `data/sources.yaml`. No source → no write.
> - Don't over-model: uncontestable scalars (a Hebrew lemma) stay plain.
>
> ## Update rules (an accumulating KB lives or dies by these)
>
> - Imports are **additive and idempotent**, keyed on `(entity_id, source, field)`. Re-running an import must produce **zero churn**.
> - **NEVER auto-overwrite a `confirmed: true` claim.** On conflict, write to the review queue, not the field.
> - Appearances dedupe by ref; candidates append on new `(value, source)`; new entity → new `stub` file; merges leave a tombstone.
>
> ## Contested by design
>
> - Plant identifications and disputed place coordinates are **multi-valued**. Keep all candidates; mark one for display (`display_taxon` / chosen coordinate). Never collapse dissent to force a single answer.
>
> ## Licensing
>
> - Respect `license` in the source registry. **Löw = public domain (extractable); Feliks = in-copyright (adjudicate/cite only, do not bulk-redistribute).** The underlying Mishnah text is public domain; project-authored material is MIT (see the repo README).
>
> ## Validation
>
> - Every `data/**/*.yaml` must validate against its `schema/*.schema.json`. A file that doesn't validate doesn't land (pre-commit + CI). Run `scripts/kb-validate.py`.
>
> ## The detector comes later
>
> - The Mishnah entity detector (`scripts/kb-detect.py`) is **one writer among several**. It only emits appearances and proposes `stub` entities. It must not overwrite identifications or biographical facts.
