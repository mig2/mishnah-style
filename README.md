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

| Masechet | Skill Version | Generated |
| --- | --- | --- |
| [Brachot](masechot/brachot.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Peah](masechot/peah.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Demai](masechot/demai.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Kilayim](masechot/kilayim.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Sheviit](masechot/sheviit.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Terumot](masechot/terumot.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Maaserot](masechot/maaserot.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Maaser Sheni](masechot/maaser-sheni.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Challah](masechot/challah.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Orlah](masechot/orlah.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Bikkurim](masechot/bikkurim.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Shabbat](masechot/shabbat.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Eruvin](masechot/eruvin.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Pesachim](masechot/pesachim.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Shekalim](masechot/shekalim.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Yoma](masechot/yoma.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Sukkah](masechot/sukkah.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Beitzah](masechot/beitzah.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Rosh Hashanah](masechot/rosh-hashanah.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Taanit](masechot/taanit.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Megillah](masechot/megillah.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Moed Katan](masechot/moed-katan.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Chagigah](masechot/chagigah.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Yevamot](masechot/yevamot.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Ketubot](masechot/ketubot.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Nedarim](masechot/nedarim.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Nazir](masechot/nazir.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Sotah](masechot/sotah.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Gittin](masechot/gittin.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Kiddushin](masechot/kiddushin.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-13 |
| [Bava Kamma](masechot/bava-kamma.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-14 |
| [Bava Metzia](masechot/bava-metzia.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-14 |
| [Bava Batra](masechot/bava-batra.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-14 |
| [Sanhedrin](masechot/sanhedrin.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-14 |
| [Makkot](masechot/makkot.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-14 |
| [Shevuot](masechot/shevuot.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-14 |
| [Eduyot](masechot/eduyot.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-14 |
| [Avodah Zarah](masechot/avodah-zarah.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-14 |
| [Avot](masechot/avot.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-14 |
| [Horayot](masechot/horayot.html) | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) | 2026-04-14 |
| [Zevachim](masechot/zevachim.html) | [`3508f92`](https://github.com/mig2/mishnah-style/tree/3508f92/.claude/skills/mishnah) | 2026-04-20 |
| [Menachot](masechot/menachot.html) | [`3508f92`](https://github.com/mig2/mishnah-style/tree/3508f92/.claude/skills/mishnah) | 2026-04-20 |
| [Chullin](masechot/chullin.html) | [`d0ddbf8`](https://github.com/mig2/mishnah-style/tree/d0ddbf8/.claude/skills/mishnah) | 2026-04-16 |
| [Bekhorot](masechot/bekhorot.html) | [`d0ddbf8`](https://github.com/mig2/mishnah-style/tree/d0ddbf8/.claude/skills/mishnah) | 2026-04-16 |
| [Arakhin](masechot/arakhin.html) | [`d0ddbf8`](https://github.com/mig2/mishnah-style/tree/d0ddbf8/.claude/skills/mishnah) | 2026-04-16 |
| [Temurah](masechot/temurah.html) | [`d0ddbf8`](https://github.com/mig2/mishnah-style/tree/d0ddbf8/.claude/skills/mishnah) | 2026-04-16 |
| [Keritot](masechot/keritot.html) | [`d0ddbf8`](https://github.com/mig2/mishnah-style/tree/d0ddbf8/.claude/skills/mishnah) | 2026-04-16 |
| [Meilah](masechot/meilah.html) | [`d0ddbf8`](https://github.com/mig2/mishnah-style/tree/d0ddbf8/.claude/skills/mishnah) | 2026-04-16 |
| [Tamid](masechot/tamid.html) | [`d0ddbf8`](https://github.com/mig2/mishnah-style/tree/d0ddbf8/.claude/skills/mishnah) | 2026-04-16 |
| [Middot](masechot/middot.html) | [`d0ddbf8`](https://github.com/mig2/mishnah-style/tree/d0ddbf8/.claude/skills/mishnah) | 2026-04-16 |
| [Kinnim](masechot/kinnim.html) | [`d0ddbf8`](https://github.com/mig2/mishnah-style/tree/d0ddbf8/.claude/skills/mishnah) | 2026-04-16 |
| [Ohalot](masechot/ohalot.html) | [`a2ba912`](https://github.com/mig2/mishnah-style/tree/a2ba912/.claude/skills/mishnah) | 2026-04-17 |
| [Makhshirin](masechot/makhshirin.html) | [`a2ba912`](https://github.com/mig2/mishnah-style/tree/a2ba912/.claude/skills/mishnah) | 2026-04-17 |
| [Zavim](masechot/zavim.html) | [`a2ba912`](https://github.com/mig2/mishnah-style/tree/a2ba912/.claude/skills/mishnah) | 2026-04-17 |
| [Tevul Yom](masechot/tevul-yom.html) | [`a2ba912`](https://github.com/mig2/mishnah-style/tree/a2ba912/.claude/skills/mishnah) | 2026-04-17 |
| [Yadayim](masechot/yadayim.html) | [`a2ba912`](https://github.com/mig2/mishnah-style/tree/a2ba912/.claude/skills/mishnah) | 2026-04-17 |
| [Uktzin](masechot/uktzin.html) | [`a2ba912`](https://github.com/mig2/mishnah-style/tree/a2ba912/.claude/skills/mishnah) | 2026-04-17 |
| [Negaim](masechot/negaim.html) | [`a2ba912`](https://github.com/mig2/mishnah-style/tree/a2ba912/.claude/skills/mishnah) | 2026-04-19 |
| [Parah](masechot/parah.html) | [`a2ba912`](https://github.com/mig2/mishnah-style/tree/a2ba912/.claude/skills/mishnah) | 2026-04-19 |
| [Taharot](masechot/taharot.html) | [`a2ba912`](https://github.com/mig2/mishnah-style/tree/a2ba912/.claude/skills/mishnah) | 2026-04-19 |
| [Mikvaot](masechot/mikvaot.html) | [`a2ba912`](https://github.com/mig2/mishnah-style/tree/a2ba912/.claude/skills/mishnah) | 2026-04-19 |
| [Niddah](masechot/niddah.html) | [`a2ba912`](https://github.com/mig2/mishnah-style/tree/a2ba912/.claude/skills/mishnah) | 2026-04-19 |
| [Keilim](masechot/keilim.html) | [`a2ba912`](https://github.com/mig2/mishnah-style/tree/a2ba912/.claude/skills/mishnah) | 2026-04-19 |

## License

The Mishnah text is in the public domain. The formatting, style guide, and skill are available under MIT.
