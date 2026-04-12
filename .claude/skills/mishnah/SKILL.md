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

If `curl` or `WebFetch` is blocked by the network proxy, use Chrome browser MCP tools as a workaround: navigate to the API URL via JavaScript and extract the text from the page.

## HTML structure

Each masechet gets a single HTML file with:
- RTL direction, Hebrew serif fonts
- Title: מסכת {name}
- Tight TOC: "א, ב, ג..." linking to each perek (no mishna-level TOC)
- Anchor IDs on every perek (`id="perek-N"`) and mishna (`id="mishna-N-M"`) for deep-linking from external apps

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

When dispatching subagents for batch formatting, always include:
- The full style guide text (or path to read it)
- The exemplar HTML (or path to read it)
- Explicit instructions that this is editorial work requiring structural reading

## Key rules (quick reference — the style guide has full details)

- **Bold** only rabbinic names (not verbs like אוֹמֵר). Include collective bodies (חֲכָמִים, שִׁבְעִים וּשְׁנַיִם זָקֵן, בֵּית דִּין).
- **Colons** after אוֹמֵר:, before כֵּיצַד?, after זֶה הַכְּלָל:, before enumerations.
- **Em-dashes** — structural, not mechanical. Bind tight when the ruling completes the case; break after the dash when what follows starts a new unit. NEVER begin a line with —.
- **״…״** only for performative speech and referenced terms. Never for rabbinic dialogue.
- **Italics** only for Tanakh quotations.
- **כֵּיצַד** — ? at the end of the full question, not always right after the word.
- **~8 words per line**, breaking at syntactic joints. Em-dash phrases may exceed this.
- **Full stop** between opposing opinions (דִּבְרֵי רַבִּי X. וַחֲכָמִים אוֹמְרִים).
