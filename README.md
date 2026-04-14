# mishnah-style

A house style for Mishnah text — clear punctuation, elegant layout, and structural formatting that makes the rhetoric visible on the page.

This repo contains:

- **A Claude skill** (`skill/`) for formatting Mishnah text from Sefaria into styled HTML
- **[Formatted masechot](masechot/)** — the outputs, one HTML file per masechet
- **A style guide** (`skill/references/style-guide.md`) — the authoritative formatting reference

## The Style

The formatting approach treats each mishna as a rhetorical document. Line breaks, em-dashes, colons, and bold attributions work together to make the structure — case vs. ruling, opinion vs. counter-opinion, parallels and kal vachomer — visible at a glance.

Key conventions:

- **Bold** rabbinic names and collective bodies (not verbs)
- **Em-dashes** bind case to ruling, with structural line breaks
- **Colons** introduce direct statements and enumerations
- **~8 Hebrew words per line**, broken at natural syntactic joints
- **Deep-linking anchors** on every perek and mishna

## Using the Skill

### In Claude Code

```bash
# Clone and point Claude Code at the skill
git clone https://github.com/YOUR_USERNAME/mishnah-style.git
cd mishnah-style
claude  # the skill will be available automatically
```

### In Cowork

Install `mishnah-style.skill` from the repo's releases, or install the skill folder directly from the project.

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
| [Zevachim](masechot/zevachim.html) | — | — |

## License

The Mishnah text is in the public domain. The formatting, style guide, and skill are available under MIT.
