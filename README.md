# mishnah-style

A house style for Mishnah text — clear punctuation, elegant layout, and structural formatting that makes the rhetoric visible on the page.

This repo contains:

- **[Formatted masechot](masechot/)** — one HTML file per masechet, all 63 tractates
- **[Editorial style guide](docs/editorial-style.md)** — the authoritative formatting rules
- **[HTML format spec](docs/html-format.md)** — HTML structure, anchors, CSS conventions
- **Scripts** for downloading source text and formatting via LLM:
  - `scripts/download.py` — fetch raw JSON from Sefaria API
  - `scripts/format.py` — format JSON→HTML using Ollama, Anthropic API, or Claude Code
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

### Download source text

```bash
python3 scripts/download.py masechet Berakhot   # single tractate
python3 scripts/download.py seder Zeraim         # full seder
python3 scripts/download.py shas                  # all of Shas
```

Downloads raw JSON from Sefaria API v3 to `sefaria/{seder}/{tractate}/`, one file per chapter, with a `manifest.jsonl` logging URLs and timestamps.

### Format into HTML

```bash
# Local model via Ollama
python3 scripts/format.py masechet Berakhot --backend ollama --model gemma4:31B

# Anthropic API
export ANTHROPIC_API_KEY=sk-ant-...
python3 scripts/format.py masechet Berakhot --backend anthropic

# Claude Code headless
python3 scripts/format.py masechet Berakhot --backend claude-code

# Single chapter
python3 scripts/format.py masechet Berakhot --ref 3

# Single mishna
python3 scripts/format.py masechet Berakhot --ref 3:5
```

Output goes to `output/`. Progress tracking shows completion percentage and ETA.

### Verify against source

```bash
python3 scripts/verify.py masechet Berakhot            # single tractate
python3 scripts/verify.py masechet Berakhot --chapter 3 # single chapter
python3 scripts/verify.py shas                          # all of Shas
python3 scripts/verify.py shas --report output/report   # with JSON + HTML reports
```

Compares words in `masechot/*.html` against the downloaded Sefaria JSON to detect hallucinated, missing, or altered text. With `--report PATH`, writes `PATH.json` (structured data) and `PATH.html` (styled report with summary table and per-mishna diffs).

### Fix errors

```bash
# Programmatic fixes only (single-word replacements)
python3 scripts/fix.py --report output/report.json

# Programmatic + LLM regen for hallucinated mishnayot
python3 scripts/fix.py --report output/report.json --backend anthropic

# Preview without changing files
python3 scripts/fix.py --report output/report.json --dry-run
```

Reads a verification report and classifies each error as programmatic (single-word replacement — wrong consonant, ending, etc.) or regen (missing/hallucinated text needing LLM re-formatting). Without `--backend`, only programmatic fixes are applied.

## Using the Claude Code Skill

```bash
git clone https://github.com/mig2/mishnah-style.git
cd mishnah-style
claude  # the skill is available automatically
```

## Masechot

All 63 masechot formatted. Last verified and corrected against Sefaria source: [`839c964`](https://github.com/mig2/mishnah-style/tree/839c964) (2026-05-17).

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
