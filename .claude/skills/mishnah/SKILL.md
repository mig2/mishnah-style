---
name: mishnah
description: "Format Mishnah text according to house style. Use this skill whenever the user asks to format a mishna, perek, masechet, or seder. Also use when the user mentions Sefaria, Mishnah formatting, or asks to work on any tractate. This skill MUST be consulted before formatting any Mishnah text — it contains the authoritative style rules, accumulated editorial refinements, and a gold-standard exemplar."
---

# Mishnah Formatting Skill

Format Mishnah text into clear, elegant, readable Hebrew HTML following a carefully developed house style.

## Before formatting anything

1. **Read the style guide**: `references/style-guide.md` — this is the complete, authoritative set of formatting rules. Read it in full before touching any text.
2. **Study the exemplar**: `references/exemplar-zevachim-1.html` — this is a gold-standard formatted perek (Zevachim chapter 1, 4 mishnayot). Study how every rule is applied in practice. Pay attention to where em-dashes bind tight vs. break, where colons fall, how line breaks create structural parallels.

## Fetching text

Use the Sefaria API v3 to fetch raw text:
```
https://www.sefaria.org/api/v3/texts/Mishnah_{Tractate}.{Chapter}
```
The response JSON has `versions[0].text` containing an array of mishnayot.

**Preferred method**: Use `curl` piped through a Python script to strip HTML tags and extract clean text. This avoids WebFetch's AI summarizer, which may truncate long mishnayot or refuse to return full text:

```bash
curl -s 'https://www.sefaria.org/api/v3/texts/Mishnah_{Tractate}.{Chapter}' | python3 -c "
import json, sys, re
data = json.load(sys.stdin)
texts = data['versions'][0]['text']
for i, t in enumerate(texts):
    clean = re.sub(r'<[^>]+>', '', t)
    print(f'{i+1}. {clean}')
"
```

**Fallback**: WebFetch works for shorter chapters but may summarize or refuse long ones. If using WebFetch, explicitly request "COMPLETE text, every word, do NOT truncate."

**Sefaria transliterations** can be tricky. If a 404 occurs, try alternate spellings (e.g. `Oktzin` not `Uktzin`, `Tevul_Yom` with underscore).

## HTML structure

Each masechet gets a single HTML file with:
- RTL direction, Hebrew serif fonts
- Meta tags for skill version and formatted date
- Title: מסכת {name}
- Tight TOC: "א, ב, ג..." linking to each perek (no mishna-level TOC)
- Anchor IDs on every perek (`id="perek-N"`) and mishna (`id="mishna-N-M"`) for deep-linking from external apps

### Meta tags (required)

Every generated HTML file must include these meta tags in the `<head>`:

```html
<meta name="mishnah-style-version" content="{GIT_SHA}">
<meta name="formatted-date" content="{YYYY-MM-DD}">
```

Use the current short SHA of HEAD (`git rev-parse --short HEAD`) for the version, and today's date. These allow tracking which skill version produced each file.

### Template

Use an existing masechet file (e.g. `masechot/kinnim.html`) as the CSS/HTML template. Copy the exact `<style>` block — do not invent new styles.

```html
<div class="perek" id="perekN">
  <h2 class="perek-title"><a id="perek-N"></a>פרק ORDINAL</h2>
  <div class="mishna" id="mN-M">
    <p class="mishna-label"><a id="mishna-N-M"></a><b>HEBREW_NUM</b></p>
    <p class="mishna-text">
      ...formatted text with <br> breaks...
    </p>
  </div>
</div>
```

Perek titles use "פרק" followed by the Hebrew ordinal (ראשון, שני, שלישי, etc.).
Mishna labels use Hebrew letter numerals (א:א, ב:ג, י״א:ד, etc.).

## The editorial process

Formatting Mishnah is EDITORIAL work, not mechanical text processing. For each mishna:

1. **Read the whole mishna first.** Understand the structure — who is speaking, what is the case, what is the ruling, where opinions are contrasted, where parallels exist.
2. **Identify the rhetorical structure.** Case vs. ruling, opinion vs. counter-opinion, question vs. answer, parallel formulations.
3. **Then punctuate and lay out.** Apply the style guide rules with the structure in mind. Every em-dash placement, every line break, every colon should reflect the mishna's logic.

## Key rules (quick reference — the style guide has full details)

- **Bold** only rabbinic names (not verbs like אוֹמֵר). Include collective bodies (חֲכָמִים, שִׁבְעִים וּשְׁנַיִם זָקֵן, בֵּית דִּין).
- **Colons** after אוֹמֵר:, before כֵּיצַד?, after זֶה הַכְּלָל:, before enumerations.
- **Em-dashes** — structural, not mechanical. Bind tight when the ruling completes the case; break after the dash when what follows starts a new unit. NEVER begin a line with —.
- **״…״** only for performative speech and referenced terms. Never for rabbinic dialogue.
- **Italics** only for Tanakh quotations.
- **כֵּיצַד** — ? at the end of the full question, not always right after the word.
- **~8 words per line**, breaking at syntactic joints. Em-dash phrases may exceed this.
- **Full stop** between opposing opinions (דִּבְרֵי רַבִּי X. וַחֲכָמִים אוֹמְרִים).

### Line length — common mistake

**Do NOT over-break lines.** The ~8 word target means 6–10 words per line. If a clause is only 3–4 words, combine it with the next clause on one line. Short parallel clauses like "חַטַּאת הָעוֹף נַעֲשֵׂית לְמַטָּה, וְחַטַּאת בְּהֵמָה לְמַעְלָה" belong on ONE line (~7 words), not two lines of 4 and 3.

**After formatting, scan for lines under 5 words and combine where syntactically natural.**

## Workflow: formatting a full seder

### Do NOT use parallel agents

Masechet formatting is output-heavy work. Each file is 300–1500 lines of nikkud-marked Hebrew HTML. Hebrew tokenizes 2–3x worse than English/code. Parallel agents will hit rate limits and waste tokens. See `docs/token-analysis-kodashim.md` for data.

### Recommended workflow

1. **Work sequentially**, one masechet at a time from the main thread
2. **Fetch all raw text first** for a masechet (cheap input tokens), save to a checkpoint file
3. **Then format and write** the HTML (expensive output tokens)
4. **Save intermediate state** — if the masechet is large (10+ chapters), write in incremental edits (chapters 1–5, then 6–10, etc.) so a rate limit doesn't lose all work
5. **Start with the largest masechot** when the rate-limit window is fresh
6. **Budget ~5–8k tokens per chapter**. A 14-chapter masechet costs ~40–80k tokens. A full seder of 11 masechot may span 2–3 sessions.

### After each masechet

- Update `masechot/index.html` with the new entry
- Update `README.md` table with the masechet, skill version, and date
