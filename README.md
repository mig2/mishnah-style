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

| Masechet     | Skill Version |
| ------------ | ------------- |
| Brachot      | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Peah         | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Demai        | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Kilayim      | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Sheviit      | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Terumot      | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Maaserot     | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Maaser Sheni | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Challah      | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Orlah        | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Bikkurim     | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Shabbat      | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Eruvin       | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Pesachim     | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Shekalim     | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Yoma         | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Sukkah       | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Beitzah      | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Rosh Hashanah| [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Taanit       | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Megillah     | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Moed Katan   | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Chagigah     | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Yevamot      | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Ketubot      | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Nedarim      | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Nazir        | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Sotah        | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Gittin       | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Kiddushin    | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Bava Kamma   | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Bava Metzia  | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Bava Batra   | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Sanhedrin    | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Makkot       | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Shevuot      | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Eduyot       | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Avodah Zarah | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Avot         | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Horayot      | [`b43da09`](https://github.com/mig2/mishnah-style/tree/b43da09/.claude/skills/mishnah) |
| Zevachim     | — |

## License

The Mishnah text is in the public domain. The formatting, style guide, and skill are available under MIT.
