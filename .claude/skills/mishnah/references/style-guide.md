# Mishnah House Style Guide

This is the authoritative reference for formatting Mishnah text. Read this entire document before formatting any mishna.

## 1. Punctuation Principles

Punctuate with a light editorial hand. The goal is clarity and readability, not heavy annotation. Read the full structure of each mishna before placing any punctuation.

### Colons
Use colons to introduce what follows:
- After אוֹמֵר / אוֹמְרִים when a rabbi's statement follows
- Before כֵּיצַד? or after זֶה הַכְּלָל
- Before a formal enumeration (e.g. "בְּאַרְבָּעָה דְבָרִים:")

### Full stops between opposing views
When a mishna presents one opinion, then closes it with "דִּבְרֵי רַבִּי X," followed by an opposing view like "וַחֲכָמִים אוֹמְרִים," use a full stop between the two views. Prefer a full stop over a semicolon unless the syntax clearly calls for tighter continuity.

### Semicolons
Use for tighter continuity within a list of related cases that parallel each other.

### Em-dashes (—)
Em-dashes set off a ruling from its case, or mark a logical turn. Their placement is STRUCTURAL, not mechanical — it depends on reading the mishna's rhetoric:

**Bind tight (keep on one line)** when the result is a short ruling that completes the case:
- כָּל הַזְּבָחִים שֶׁנִּזְבְּחוּ שֶׁלֹּא לִשְׁמָן — כְּשֵׁרִים,
- וְהַחַטָּאת וְהָאָשָׁם — לְשֵׁם חֵטְא.

**Break after the dash** when what follows starts a new structural unit — a parallel, a kal vachomer, a new opinion:
- רַבִּי אֱלִיעֶזֶר אוֹמֵר: אַף הָאָשָׁם —  [line break]
  הַפֶּסַח בִּזְמַנּוֹ, וְהַחַטָּאת וְהָאָשָׁם בְּכָל זְמָן.
  (so the line echoes the earlier parallel "הַפֶּסַח בִּזְמַנּוֹ, וְהַחַטָּאת בְּכָל זְמָן")
- הַחַטָּאת בָּאָה עַל חֵטְא, וְהָאָשָׁם בָּא עַל חֵטְא —  [line break]
  מַה חַטָּאת פְּסוּלָה שֶׁלֹּא לִשְׁמָהּ,
  (because מַה starts a kal vachomer that binds forward, not back)
- הַפֶּסַח שֶׁשְּׁחָטוֹ בְשַׁחֲרִית בְּאַרְבָּעָה עָשָׂר שֶׁלֹּא לִשְׁמוֹ —  [line break]
  רַבִּי יְהוֹשֻׁעַ מַכְשִׁיר...
  (because the rabbi's opinion is a new structural unit)

**ABSOLUTE RULE**: An em-dash must NEVER appear at the beginning of a line. If a line would start with —, either pull the dash onto the end of the previous line (even exceeding ~8 words) or restructure the break earlier (e.g. break after a colon).

**Visual wrapping**: A dash at the end of a very long line (12+ words) may wrap to its own visual line in the browser, even though the source has it on the same line. This is just as bad as starting a line with —. If a case clause is long enough that the trailing dash would wrap, break the clause earlier so the dash sits on a shorter line:
  ✗ כָּל הַקֳּדָשִׁים שֶׁהִקְדִּישָׁן בִּשְׁעַת אִסּוּר בָּמוֹת וְהִקְרִיבָן בִּשְׁעַת אִסּוּר בָּמוֹת בַּחוּץ —
  ✓ כָּל הַקֳּדָשִׁים שֶׁהִקְדִּישָׁן בִּשְׁעַת אִסּוּר בָּמוֹת [break]
    וְהִקְרִיבָן בִּשְׁעַת אִסּוּר בָּמוֹת בַּחוּץ —

Ask yourself: does what follows the dash complete the preceding phrase (bind tight), or does it begin a new unit (break after dash)? Structural echoes and rhetorical parallels between lines matter more than a fixed word count.

## 2. Bolding

Bold **all rabbinic attributions**:
- Named rabbis: **רַבִּי עֲקִיבָא**, **רַבָּן גַּמְלִיאֵל**, **בֶּן עַזַּאי**
- Collective bodies: **חֲכָמִים**, **שִׁבְעִים וּשְׁנַיִם זָקֵן** (the Sanhedrin), **בֵּית דִּין**
- Bold ONLY the name — never include the verb. Write `<b>רַבִּי שִׁמְעוֹן</b> אוֹמֵר:` not `<b>רַבִּי שִׁמְעוֹן אוֹמֵר</b>:`

## 3. Quotation Marks

Use ״…״ (high-high gershayim, U+05F4) ONLY for:
- **Performative speech**: oaths, vows, declarations a person utters (e.g. ״שְׁבוּעָה שֶׁאֶתֵּן לְאִישׁ פְּלוֹנִי״)
- **Terms referenced from a prior mishna**: when כֵּיצַד quotes a category (e.g. כֵּיצַד ״לִשְׁמָן וְשֶׁלֹּא לִשְׁמָן״?)

Do NOT put quotation marks around rabbinic dialogue or debate (אָמַר לוֹ רַבִּי עֲקִיבָא...).

## 4. Italics

Italicize ONLY direct Tanakh quotations. Keep biblical references (book/chapter) outside the italics.

## 5. כֵּיצַד Structure

Pay close attention to whether כֵּיצַד stands alone or is mid-sentence:
- **Standalone**: כֵּיצַד? on its own line, answer begins next line
- **Case-opener**: When כֵּיצַד? immediately introduces a specific case rather than a general "how so?", join it with the opening of the case on the same line to avoid a 1-word line:
  ✓ כֵּיצַד? הַשּׁוֹחֵט אֶת הַתּוֹדָה
  ✗ כֵּיצַד? [alone on line]
    הַשּׁוֹחֵט אֶת הַתּוֹדָה [next line]
- **Mid-question**: the ? goes at the end of the FULL question:
  ✓ חַטַּאת הָעוֹף, כֵּיצַד הָיְתָה נַעֲשֵׂית?
  ✗ חַטַּאת הָעוֹף כֵּיצַד? הָיְתָה נַעֲשֵׂית?

Read the full sentence before placing the question mark.

## 6. Line Layout

Cap lines at roughly **8 Hebrew words**, breaking at natural syntactic joints. Lines can range 6–10 words; the ~8 target is a guideline, not a straitjacket.

Break at: clause boundaries, colons (especially after אוֹמֵר:), periods, semicolons.

Exception: an em-dash phrase may exceed ~8 words to keep the bound phrase intact.

When laying out lines, think about **structural parallels**. If two lines echo each other (e.g. the stam's ruling and a rabbi's modification of it), align them so the difference is visible.

## 7. Rhetorical Structure

Before punctuating any mishna, identify:
- **Case vs. ruling**: what is the scenario, what is the law?
- **Opinion vs. counter-opinion**: where does one view end and another begin?
- **Question vs. answer**: especially in כֵּיצַד structures
- **Parallels**: repeated formulations where a small change carries the argument

Use line breaks, punctuation, and em-dashes to make these structures visually clear. The reader should be able to see the logic of the mishna from the layout alone.
