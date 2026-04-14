# Masechet HTML Format

Each masechet is a single self-contained HTML file. This document describes the structure, conventions, and anchor scheme used across all files.

## Document structure

```
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="mishnah-style-version" content="{SHA}">
  <meta name="formatted-date" content="{YYYY-MM-DD}">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>מסכת {name}</title>
  <style>...</style>
</head>
<body>
  <h1 class="masechet-title">...</h1>
  <nav class="toc">...</nav>
  <div class="perek">...</div>
  ...
</body>
</html>
```

### Meta tags

| Name | Description |
| --- | --- |
| `mishnah-style-version` | Short git SHA of the latest commit touching `.claude/skills/mishnah/` at the time the file was generated. |
| `formatted-date` | ISO 8601 date (`YYYY-MM-DD`) when the file was generated. |

## Page elements

### Title

```html
<h1 class="masechet-title"><a id="top"></a>מסכת ברכות</h1>
```

The masechet name in Hebrew, centered. The `top` anchor allows linking to the page head.

### Table of contents

```html
<nav class="toc">
  <a href="#perek-1">א</a> <span class="sep">·</span>
  <a href="#perek-2">ב</a> <span class="sep">·</span>
  ...
</nav>
```

A single line of Hebrew-letter links to each perek, separated by `·` dots. No mishna-level entries in the TOC.

### Perek

```html
<div class="perek" id="perekN">
  <h2 class="perek-title"><a id="perek-N"></a>פרק {ordinal}</h2>
  ...mishnayot...
</div>
```

- `id="perekN"` on the div (no hyphen, e.g. `perek1`)
- `id="perek-N"` on the anchor inside the heading (with hyphen, e.g. `perek-1`) — this is the deep-link target
- The heading uses the Hebrew ordinal: ראשון, שני, שלישי, רביעי, חמישי, שישי, שביעי, שמיני, תשיעי, עשירי, אחד עשר, שנים עשר, etc.

### Mishna

```html
<div class="mishna" id="mN-M">
  <p class="mishna-label"><a id="mishna-N-M"></a><b>א:א</b></p>
  <p class="mishna-text">
    ...formatted text with <br> line breaks...
  </p>
</div>
```

- `id="mN-M"` on the div (e.g. `m1-1`, `m3-7`)
- `id="mishna-N-M"` on the anchor (e.g. `mishna-1-1`, `mishna-3-7`) — the deep-link target
- The label uses Hebrew numerals for both perek and mishna, separated by a colon: `א:א`, `ב:ג`, `י״א:ד`

## Anchor scheme

External applications can deep-link to any perek or mishna:

| Target | Anchor format | Example |
| --- | --- | --- |
| Page top | `#top` | `brachot.html#top` |
| Perek | `#perek-{N}` | `brachot.html#perek-3` |
| Mishna | `#mishna-{N}-{M}` | `brachot.html#mishna-3-5` |

`N` is the 1-based perek number, `M` is the 1-based mishna number within the perek. Both use Arabic numerals in the anchor ID.

## Inline formatting

The mishna text within `<p class="mishna-text">` uses the following inline markup:

| Element | Usage |
| --- | --- |
| `<b>` | Rabbinic names and collective bodies (never verbs). E.g. `<b>רַבִּי עֲקִיבָא</b> אוֹמֵר:` |
| `<i>` | Direct Tanakh quotations only. Biblical references (book/chapter) are kept outside the italics. |
| `<br>` | Line breaks at ~8 Hebrew words, placed at syntactic joints (clause boundaries, colons, periods). |

## Punctuation conventions

| Mark | Usage |
| --- | --- |
| `:` (colon) | After אוֹמֵר/אוֹמְרִים before a statement; before כֵּיצַד?; after זֶה הַכְּלָל; before enumerations. |
| `.` (full stop) | Between opposing opinions (דִּבְרֵי רַבִּי X. וַחֲכָמִים אוֹמְרִים). |
| `;` (semicolon) | Tighter continuity within parallel cases. |
| `—` (em-dash) | Separates case from ruling. Binds tight when the ruling is short; line-breaks after the dash when a new structural unit follows. Never appears at the start of a line. |
| `?` (question mark) | After כֵּיצַד (standalone or at the end of a full mid-sentence question). |
| `״…״` (gershayim) | Performative speech (oaths, vows, declarations) and terms referenced from a prior mishna. Never used for rabbinic dialogue. |

## CSS

All styling is embedded in a `<style>` block in the `<head>`. No external stylesheets. Key properties:

- **Font stack**: SBL Hebrew, Frank Ruehl CLM, Ezra SIL, David CLM, Noto Serif Hebrew, Times New Roman, serif
- **Font size**: 1.2rem body, 2rem title, 1.5rem perek headings
- **Line height**: 2 (generous for Hebrew readability)
- **Max width**: 42em, centered with auto margins
- **Background**: `#fdfdfa` (warm off-white)
- **Link color**: `#2a5a8a`

## File naming

Files are named using transliterated masechet names in lowercase with hyphens:

```
brachot.html
bava-kamma.html
moed-katan.html
rosh-hashanah.html
maaser-sheni.html
avodah-zarah.html
```
