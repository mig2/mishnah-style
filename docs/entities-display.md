# Mishnah Entities — Display & UX Spec

**Status:** v0 (foundational). This spec defines how the people, places, and plants in the [entities knowledge base](entities-knowledge-base.md) are *displayed* to a reader — the rendered views and the in-text overlay. It is deliberately separate from the KB spec: the knowledge base is the source of truth and knows nothing about presentation; everything here is a **derived view** on top of it.

It builds on two existing repo conventions: the masechet HTML structure and deep-link anchors in [`docs/html-format.md`](html-format.md), and the word-normalization pipeline in [`docs/how-verify-works.md`](how-verify-works.md), which phase 3 reuses.

-----

## 1. Principle: the canonical text is never touched

The committed `masechot/*.html` files are the canonical reading artifacts. **The display layer never edits them.** All entity presentation is produced into *separate, derived, regenerable* artifacts (gitignored, like `knowledge.db`, `sefaria/`, and `output/`). Re-running the build reproduces them exactly; deleting them loses nothing.

This keeps the house style (`docs/editorial-style.md`) and word-fidelity guarantee (`verify.py`) completely insulated from anything we do for entities.

-----

## 2. Two visual states

The enriched reading view has two states:

1. **Default — invisible.** It reads identically to the canonical masechet. No color, no underlines, no icons in the running text. A reader who never touches the controls sees the pure text.
2. **Overlay on — quiet color.** Toggling brings up a color overlay on entity mentions:

   | Type | Color | Icon |
   | --- | --- | --- |
   | Plants | green | 🌿 |
   | Places | red | 📍 |
   | People | blue | 👤 |

   Each colored mention is a link to that entity's page (§5). Toggles are **per-type and independent** — a reader studying *Kilayim* can light up only plants; one reading *Avot* can light up only people.

The icons are used in the toggle controls, the legend, and on entity pages. The *inline* overlay is color-only by default (see the accessibility note in §3).

-----

## 3. Color & accessibility

The palette is green / red / blue as above. **Known issue, recorded for follow-up:** red (places) and green (plants) collide for red-green color vision deficiency (~8% of men), and the inline overlay is the one surface that carries color *without* an accompanying icon.

Mitigations, ranked, to decide before any public release (not a blocker for dev — dev uses the palette as described):

1. **Distinct underline styles per type** (e.g. plants dotted, places dashed, people solid) layered under the color, so the cue survives without color.
2. **A small leading icon** on inline mentions — reuses 🌿/📍/👤, but adds visual weight to the running text.
3. **A colorblind-safe palette** swap (e.g. blue / orange / teal).

Everywhere *outside* the running text (toggles, legend, entity pages), the per-type icon already provides a non-color channel, so those surfaces are fine as-is.

-----

## 4. Build pipeline — three phases, each a view on the one below

```
data/**.yaml ──kb-build──▶  knowledge.db                 (1) source of truth → SQLite index
knowledge.db ──kb-render─▶  entity pages                  (2) one HTML page per entity
                          + map / flora-gallery / index       (pure DB views; no mishna text)
masechot/*.html + DB ──kb-enrich─▶  enriched masechot     (3) mark mishna mentions in the text,
                                                                link each to its (2) page
```

The order matters and is intentional:

- **Phase 1 — `scripts/kb-build.py`** compiles the YAML into `knowledge.db` (per the KB spec §11). Nothing here is presentational.
- **Phase 2 — `scripts/kb-render.py`** generates the standalone, DB-only views: one **entity page** per person/place/plant (§5), plus aggregate views — a **places map**, a **flora gallery**, and a **who's-who / index**. These never contain mishna text; they are pure projections of the KB.
- **Phase 3 — `scripts/kb-enrich.py`** is the *join*, and therefore last: it takes a canonical masechet plus the DB and produces an **enriched copy** in which entity mentions in the running text are wrapped, colored (under the overlay), and linked to the phase-2 entity pages. It depends on phase 2 (the link targets must exist) and on the appearance linkage (to know which mishnayot mention what).

All phase-2 and phase-3 outputs are derived artifacts: gitignored, regenerable, output to a build/publish directory rather than committed over `masechot/`.

-----

## 5. Entity pages — the canonical info surface

Clicking an entity opens its **own page** (a real page in a new tab — the "popup"), not just a tooltip. This is deliberate: the same page is what the map, gallery, and index link to, so each entity has **one canonical surface**, and that surface has room a tooltip never would.

Each entity page carries, by type:

- **People** — names (he/en/variants), generation & floruit, relationships (teachers/students, as links to their pages), bio claims.
- **Places** — a map at the displayed coordinate, photo, region; classical/modern names.
- **Plants** — image/illustration, display taxon, botanical/common names.

And for **all** types, the big payoff a tooltip can't give: **every appearance across all 63 masechot**, as deep links into the enriched text via the existing anchor scheme (`masechot/{slug}.html#mishna-N-M`).

### Contested facts must stay visible

The KB keeps dissent on purpose (multiple plant candidates, disputed coordinates); the entity page must not flatten it:

- **Plants** — show the display taxon prominently, then list the other candidates with their source and confidence (e.g. *identified as Origanum syriacum (Feliks); also proposed: Satureja thymbra (minority)*).
- **Places** — when `consensus` is `disputed`, show it as disputed and surface the competing coordinates/sources rather than silently picking one pin.

-----

## 6. Phase 3 — anchoring entity words (the keystone, and the finicky part)

Appearances in the KB are **mishna-granular** (`shekalim 4:2`); the overlay needs the **exact word(s)** to color and link. Resolution (chosen approach, revisable):

- `kb-enrich` **matches surface forms** drawn from the entity's `names` / `variants` against the mishna's running text.
- It does so through **`verify.py`'s normalization pipeline** — nikkud stripping, final-letter folding, double-vav normalization (`docs/how-verify-works.md`) — so a match survives vowelization and spelling variance. Reusing that pipeline means the matcher is built on logic the project already trusts.

This keeps span-finding out of the detector (which stays mishna-granular). It is expected to be the **finicky** part — inflection, construct forms, and multi-word terms will need iteration — and is the natural first place to invest once the views exist. If surface matching proves too lossy, the fallback is to have the detector emit character offsets; we deliberately defer that cost until proven necessary.

-----

## 7. Ambiguous matches (open design, for phase 3)

A surface form can legitimately resolve to **more than one** entity (two places sharing a name; a word that is both a plant term and a name). Both candidate entities already exist as phase-2 pages, so a marked mention can become a **choice between them** rather than a single link. Direction, to be finalized in phase 3:

- **Mark only when resolvable.** If the appearance for that mishna disambiguates the mention, link straight to the right page. **Never guess** — an unmarked word is better than a wrong link.
- **When genuinely ambiguous, present the choice rather than suppressing it.** Options to weigh: a small disambiguation chooser (a popover listing the candidate pages), or a distinct "ambiguous" styling that links to a tiny chooser surface. Since both targets exist in the rendered set, the link is naturally "this or that."

This is recorded as an open item; the matcher in §6 and this section will be designed together.

-----

## 8. Implementation notes

- **JS-free reading view.** The overlay toggle is **CSS-only** (a hidden checkbox per type + `:checked ~` rules flipping the span colors), so the enriched masechot stay static, offline, and printable. The only interactive surfaces are the entity pages themselves (and even those can start as plain pages).
- **No markup in the canonical files.** Wrapping happens only in the enriched copies. (For the record, this is safe regardless: `verify.py` strips all tags before word comparison, so entity spans never affect fidelity — but we keep the canonical files clean as a matter of principle.)
- **Scripts** live in the shared `scripts/` directory alongside the rest of the pipeline: `kb-render.py` (phase 2), `kb-enrich.py` (phase 3).
- **Artifacts** (entity pages, map, gallery, index, enriched masechot) are derived and gitignored.

-----

## 9. Open items

1. **Colorblind-safe treatment of the inline overlay** (§3) — pick a mitigation before public release.
2. **Word anchoring** (§6) — surface-form matching is expected to need iteration; detector offsets remain a fallback.
3. **Ambiguous matches** (§7) — finalize the chooser vs. distinct-styling approach.
4. **Map / gallery / index detail** — layout of the aggregate phase-2 views is not yet specified.
