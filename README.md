# mishnah-style

A house style for Mishnah text — clear punctuation, elegant layout, and structural formatting that makes the rhetoric visible on the page.

This repo contains:

- **A Claude skill** (`skill/`) for formatting Mishnah text from Sefaria into styled HTML
- **Formatted masechot** (`masechot/`) — the outputs, one HTML file per masechet
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

| Masechet     | Status |
| ------------ | ------ |
| Brachot      | Draft  |
| Peah         | Draft  |
| Demai        | Draft  |
| Kilayim      | Draft  |
| Sheviit      | Draft  |
| Terumot      | Draft  |
| Maaserot     | Draft  |
| Maaser Sheni | Draft  |
| Challah      | Draft  |
| Orlah        | Draft  |
| Bikkurim     | Draft  |
| Shabbat      | Draft  |
| Eruvin       | Draft  |
| Pesachim     | Draft  |
| Shekalim     | Draft  |
| Yoma         | Draft  |
| Sukkah       | Draft  |
| Beitzah      | Draft  |
| Rosh Hashanah| Draft  |
| Taanit       | Draft  |
| Megillah     | Draft  |
| Moed Katan   | Draft  |
| Chagigah     | Draft  |
| Yevamot      | Draft  |
| Ketubot      | Draft  |
| Nedarim      | Draft  |
| Nazir        | Draft  |
| Sotah        | Draft  |
| Gittin       | Draft  |
| Kiddushin    | Draft  |
| Zevachim     | Draft  |

## License

The Mishnah text is in the public domain. The formatting, style guide, and skill are available under MIT.
