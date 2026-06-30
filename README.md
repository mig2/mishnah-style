# mishnah-style

A house style for Mishnah text — clear punctuation, elegant layout, and structural formatting that makes the rhetoric visible on the page.

This repo contains:

- **[Formatted masechot](masechot/)** — one HTML file per masechet, all 63 tractates, verified clean against Sefaria
- **Documentation**:
  - [Editorial style guide](docs/editorial-style.md) — the authoritative formatting rules
  - [HTML format spec](docs/html-format.md) — HTML structure, anchors, CSS conventions
  - [How verification works](docs/how-verify-works.md) — normalization pipeline and comparison logic
  - [Verification report](docs/verification-report.md) — error categories found and lessons learned
  - [Entities knowledge base](docs/entities-knowledge-base.md) — design spec for an accumulating store of people, places, and plants in the Mishnah (v0, foundational)
  - [Entities display & UX](docs/entities-display.md) — how entities are rendered: the in-text color overlay and the derived entity/map/gallery views (v0, foundational)
- **Scripts** — full pipeline for downloading, formatting, verifying, fixing, and merging:
  - `scripts/download.py` — fetch raw JSON from Sefaria API
  - `scripts/format.py` — format JSON using Ollama, Anthropic API, or Claude Code
  - `scripts/verify.py` — cross-check HTML against Sefaria source
  - `scripts/fix.py` — programmatic fixes + LLM regen for errors
  - `scripts/merge.py` — apply JSON corrections into HTML files
  - `scripts/update-readme.py` — regenerate masechot table from meta tags
- **Entities knowledge base** (`entities/`) — an accumulating store of people, places, and plants in the Mishnah ([KB spec](docs/entities-knowledge-base.md), [display spec](docs/entities-display.md)). YAML is the source of truth (run `pip install -r entities/requirements.txt` first):
  - `scripts/kb-validate.py` — validate `entities/data/` against the JSON schemas + semantic cross-checks
  - `scripts/kb-build.py` — compile the YAML into the derived `entities/knowledge.db`
  - `scripts/kb-render.py` — render the static entity/index/map/gallery site into `entities/site/` (display phase 2)
  - `scripts/kb-enrich.py` — weave the entity overlay (CSS-only per-type toggle + links) into copies of the masechot under `entities/site/read/` (display phase 3); canonical masechot are never modified
  - `scripts/kb-import-wikidata.py`, `scripts/kb-import-pleiades.py` — enrich entities from external sources (additive, idempotent; `--input` runs offline against `entities/fixtures/`)
  - `scripts/kb-detect.py` + `scripts/kb-promote.py` — populate the KB from the corpus: detect entities mishna-by-mishna (`--mode bold` offline, `--mode llm` on your machine), review in `entities/review/index.html`, promote into stubs / rejections / rules ([detection spec](docs/entities-detection.md))
  - `scripts/kb-selftest.py` — quick offline smoke of the §8 merge-rule invariants
  - `tests/` — full suite, one module per deliverable: `python3 -m unittest discover -s tests -t tests`
- **A Claude skill** (`.claude/skills/mishnah/`) for interactive formatting in Claude Code

## The Style

The formatting approach treats each mishna as a rhetorical document. Line breaks, em-dashes, colons, and bold attributions work together to make the structure — case vs. ruling, opinion vs. counter-opinion, parallels and kal vachomer — visible at a glance.

Key conventions:

- **Bold** rabbinic names and collective bodies (not verbs)
- **Em-dashes** bind case to ruling, with structural line breaks
- **Colons** introduce direct statements and enumerations
- **~8 Hebrew words per line**, broken at natural syntactic joints
- **Deep-linking anchors** on every perek and mishna

## Scripts

All scripts accept `masechet <name>`, `seder <name>`, or `shas` as scope. Use `--ref` to target a chapter (3) or mishna (3:5).

### Pipeline

```
download.py  → sefaria/*.json     (raw source from Sefaria)
format.py    → output/*.json      (LLM-formatted mishnayot)
verify.py    → output/*.json/html (verification report)
fix.py       → output/*.json      (corrections)
merge.py     → masechot/*.html    (applies JSON into HTML files)
```

### Download source text

```bash
python3 scripts/download.py masechet Berakhot
python3 scripts/download.py seder Zeraim
python3 scripts/download.py shas
```

### Format into JSON

```bash
python3 scripts/format.py masechet Berakhot --backend anthropic
python3 scripts/format.py masechet Berakhot --ref 3:5 --backend ollama
python3 scripts/format.py seder Zeraim --backend claude-code
python3 scripts/format.py shas --backend anthropic
```

Backends: `ollama` (local), `anthropic` (API, needs `ANTHROPIC_API_KEY`), `claude-code` (headless CLI).

### Verify against source

```bash
python3 scripts/verify.py masechet Berakhot
python3 scripts/verify.py masechet Berakhot --ref 3
python3 scripts/verify.py seder Zeraim
python3 scripts/verify.py shas --report output/report
```

With `--report PATH`, writes `PATH.json` (for fix.py) and `PATH.html` (human-readable).

### Fix errors

```bash
python3 scripts/fix.py --report output/report.json                      # programmatic only
python3 scripts/fix.py --report output/report.json --backend anthropic  # + LLM regen
python3 scripts/fix.py --report output/report.json --dry-run            # preview
```

### Merge into HTML

```bash
python3 scripts/merge.py output/keilim-fixes.json
python3 scripts/merge.py output/keilim-formatted.json
python3 scripts/merge.py output/*.json
```

Only `merge.py` writes to `masechot/`. Handles both patching existing mishnayot and inserting missing ones.

## Using the Claude Code Skill

```bash
git clone https://github.com/mig2/mishnah-style.git
cd mishnah-style
claude  # the skill is available automatically
```

## Masechot

All 63 masechot formatted. Last updated: [`44bdd8d`](https://github.com/mig2/mishnah-style/tree/44bdd8d) (2026-05-24).

| Seder | Masechot |
| --- | --- |
| Zeraim | [Brachot](masechot/brachot.html), [Peah](masechot/peah.html), [Demai](masechot/demai.html), [Kilayim](masechot/kilayim.html), [Sheviit](masechot/sheviit.html), [Terumot](masechot/terumot.html), [Maaserot](masechot/maaserot.html), [Maaser Sheni](masechot/maaser-sheni.html), [Challah](masechot/challah.html), [Orlah](masechot/orlah.html), [Bikkurim](masechot/bikkurim.html) |
| Moed | [Shabbat](masechot/shabbat.html), [Eruvin](masechot/eruvin.html), [Pesachim](masechot/pesachim.html), [Shekalim](masechot/shekalim.html), [Yoma](masechot/yoma.html), [Sukkah](masechot/sukkah.html), [Beitzah](masechot/beitzah.html), [Rosh Hashanah](masechot/rosh-hashanah.html), [Taanit](masechot/taanit.html), [Megillah](masechot/megillah.html), [Moed Katan](masechot/moed-katan.html), [Chagigah](masechot/chagigah.html) |
| Nashim | [Yevamot](masechot/yevamot.html), [Ketubot](masechot/ketubot.html), [Nedarim](masechot/nedarim.html), [Nazir](masechot/nazir.html), [Sotah](masechot/sotah.html), [Gittin](masechot/gittin.html), [Kiddushin](masechot/kiddushin.html) |
| Nezikin | [Bava Kamma](masechot/bava-kamma.html), [Bava Metzia](masechot/bava-metzia.html), [Bava Batra](masechot/bava-batra.html), [Sanhedrin](masechot/sanhedrin.html), [Makkot](masechot/makkot.html), [Shevuot](masechot/shevuot.html), [Eduyot](masechot/eduyot.html), [Avodah Zarah](masechot/avodah-zarah.html), [Avot](masechot/avot.html), [Horayot](masechot/horayot.html) |
| Kodashim | [Zevachim](masechot/zevachim.html), [Menachot](masechot/menachot.html), [Chullin](masechot/chullin.html), [Bekhorot](masechot/bekhorot.html), [Arakhin](masechot/arakhin.html), [Temurah](masechot/temurah.html), [Keritot](masechot/keritot.html), [Meilah](masechot/meilah.html), [Tamid](masechot/tamid.html), [Middot](masechot/middot.html), [Kinnim](masechot/kinnim.html) |
| Taharot | [Kelim](masechot/keilim.html), [Ohalot](masechot/ohalot.html), [Negaim](masechot/negaim.html), [Parah](masechot/parah.html), [Taharot](masechot/taharot.html), [Mikvaot](masechot/mikvaot.html), [Niddah](masechot/niddah.html), [Makhshirin](masechot/makhshirin.html), [Zavim](masechot/zavim.html), [Tevul Yom](masechot/tevul-yom.html), [Yadayim](masechot/yadayim.html), [Uktzin](masechot/uktzin.html) |

## License

The Mishnah text is in the public domain. The formatting, style guide, and skill are available under MIT.
