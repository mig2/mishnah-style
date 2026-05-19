# Verification Pipeline: Report and Lessons Learned

## Overview

The mishnah-style project formatted all 63 masechot (4192 mishnayot) using Claude as an LLM. After formatting, we built a verification pipeline to cross-check the formatted HTML against the Sefaria source text. This document records what we found, what went wrong, what we tried, and what we learned.

## Pipeline

```
download.py  → sefaria/*.json        (raw source from Sefaria API)
format.py    → output/*-formatted.json (LLM editorial formatting)
verify.py    → output/*.json + .html  (word-level diff report)
fix.py       → output/*-fixes.json    (programmatic + LLM corrections)
merge.py     → masechot/*.html        (apply corrections)
```

## Error categories found

### 1. Missing mishnayot (truncation)

The LLM would stop before finishing a chapter, dropping the last 1-5 mishnayot. This happened most often in long chapters and when session token limits were hit.

**Examples**: Peah 6:9-6:11, Demai 5:11-6:12, Beitzah 1:6-1:10, Eduyot 1:9-1:14, Avot 6:1-6:11

**Fix**: Regen via LLM. The `fix.py --backend` path handles these through `merge.py` insert.

### 2. Hallucinated/invented text

The most serious category. The LLM would write plausible-sounding mishna text instead of faithfully reproducing the source. Patterns included:

- **Continuing a theme**: Keilim 18:8 — the model wrote a mishna about מטה (beds, continuing the theme of 18:5-18:7) instead of the actual text about תפלין.
- **Expanding compressed text**: Shekalim 6:6 — source has `ששה לנדבה` but the LLM expanded it to `חמשה שנדבו דינר זהב מביאין בו עולה של שני סלעים וששה לנדבה` (adding an explanatory clause from another textual tradition).
- **Adding extra lines**: Shabbat 15:3 — LLM added `אבל לא של יום הכפורים בשבת` which exists in the source in parentheses (a textual variant), but should have been preserved as-is with the parenthesized text, not duplicated.

**Fix**: Regen via LLM, then verify the regen output (`verify.py --json`) before merging. Manual fix required when the LLM persistently hallucinates the same content.

### 3. Divine name substitution (ה → יי)

The LLM has strong priors about Hebrew scribal conventions. When it encounters a trailing ה that it interprets as an abbreviation of God's name, it "corrects" it to the traditional substitution יי (double yud).

**Examples**: 
- Megillah 3:6: `במעשה` → `במעשיי` (trailing heh of מעשה replaced with יי)
- Megillah 3:6: `ה` → `יי` in other positions

**Root cause**: The model's training data includes texts where this substitution is standard practice. It applies the convention even when instructed not to alter words.

**Fix**: Manual correction required. The LLM consistently reproduces this error on regen. Could be addressed with a programmatic post-processor that reverts יי→ה when the source has ה.

### 4. Dropped conjunctive vavs

After adding a full stop between opposing opinions (per the style guide), the LLM would drop the conjunctive vav from the following word, making it "grammatically correct" for a new sentence.

**Examples**: `וחכמים` → `חכמים`, `ובית` → `בית` (throughout Orlah, Sheviit, etc.)

**Root cause**: The style guide says to add full stops between opinions. The model interprets this as starting a new sentence and drops the vav accordingly. But the instruction is to not alter words — the vav is part of the source text.

**Fix**: Programmatic — single-word replace handled by `fix.py`. These are consistently caught and fixed.

### 5. Plural ending variations (ים → ין)

The source text uses one plural form, the LLM outputs another.

**Examples**: `נאמנים` → `נאמנין`, `חורשים` → `חורשין`, `אוכלים` → `אוכלין`

**Root cause**: Both forms are valid in Mishnaic Hebrew. The model normalizes to whichever form it's seen more often in training.

**Fix**: Programmatic — single-word replace.

### 6. Final letter errors (ן mid-word)

The LLM occasionally uses final forms (ך,ם,ן,ף,ץ) in non-final positions within a word.

**Example**: `דינו` → `דיןו` (final nun instead of regular nun mid-word)

**Root cause**: Likely a tokenization artifact — the model's Hebrew tokenizer sometimes produces tokens that end with a final letter form even when more text follows.

**Fix**: Programmatic pre-pass in `fix.py` that replaces final forms in non-final positions with their regular equivalents. Also normalized in the verifier so these don't cascade into alignment failures.

### 7. Markdown instead of HTML

The LLM occasionally falls back to markdown `**bold**` syntax instead of the requested HTML `<b>bold</b>`.

**Root cause**: The model's default formatting instinct is markdown. Despite the system prompt specifying HTML, this leaks through occasionally.

**Fix**: Verifier strips `**` markers for comparison. Style guide updated to explicitly ban markdown syntax. Ideally the `<b>` tags would be applied programmatically rather than relying on the LLM.

### 8. Biblical references without parentheses

Sefaria's source text includes biblical references in parentheses: `(ויקרא ה)`. The LLM sometimes outputs the reference without parentheses.

**Root cause**: The model sees the reference as metadata and reformats it.

**Fix**: Style guide updated to require preserving parenthesized references as-is.

## Verifier evolution

The verifier went through several iterations as we discovered false positive patterns:

### Nikkud normalization
Strip Hebrew vowel points (nikkud) before comparison. Without this, every word differs due to nikkud placement variations.

### Quote normalization
Sefaria uses ASCII `"` and `'`, the HTML uses Hebrew `״` and `׳`. Both stripped for comparison.

### Plene/defective spelling
Words like `מצוות` (plene, double vav) vs `מצות` (defective, single vav) are the same word. Double-vav normalized to single-vav for comparison.

### Final letter normalization
Final forms (ך,ם,ן,ף,ץ) in non-final positions normalized to regular forms (כ,מ,נ,פ,צ) for comparison.

### Colophon stripping
Sefaria includes scribal colophons (`סליק מסכת ...`, `הדרן עלך ...`) at the end of the last mishna. These are stripped from the normalized word list.

### Parenthetical handling (most complex)

Sefaria uses parentheses for two different purposes:
1. **Biblical references**: `(ויקרא ה)`, `(שם)`, `(שמות יז)` — editorial annotations, not part of the mishna text.
2. **Textual glosses**: `(אף הרוצה)`, `(זה הכלל)` — words that ARE part of the mishna text but marked as variant readings.

**First attempt**: Strip all parenthesized content. Result: false negatives — textual glosses were silently removed from source, so hallucinated additions of those words weren't caught.

**Second attempt**: Keep all parenthesized content as words. Result: false positives — biblical references showed as positional shifts (delete+insert pairs) because the references are in different positions in source vs HTML.

**Third attempt (incorrect)**: Cancel matching delete+insert pairs. Result: dangerous — could hide real errors where the same word was deleted from one place and added to another.

**Final approach**: Classify each parenthesized group. If it contains a biblical book name (including שם for ibid), strip entirely. Otherwise, keep the words and strip just the parens. This correctly handles both cases.

## Remaining known issues (as of 2026-05-19)

After running the full pipeline on Zeraim (clean) and Moed (6 remaining), these patterns persist:

| Tractate | Ref | Issue | Type |
|----------|-----|-------|------|
| Shekalim | 1:5 | Missing: אבל | Dropped word |
| Shekalim | 3:3 | Missing: היה | Dropped word |
| Shekalim | 4:5 | Missing: ממנה | Dropped word |
| Shekalim | 7:1 | Missing: להקל | Dropped word |
| Megillah | 3:6 | Changed: יי → ה | Divine name substitution |
| Moed Katan | 3:4 | Missing: העזרה | Dropped word |

The Shekalim and Moed Katan dropped words are single-word deletions that fix.py classifies as programmatic but may not fix correctly depending on insertion context. The Megillah issue is the persistent divine name substitution.

## Recommendations

1. **Never trust LLM output without verification**. The verify→fix→verify cycle is essential.
2. **Programmatic fixes are reliable**. Single-word replacements, final-letter corrections, and vav restorations work consistently.
3. **LLM regen is unreliable for certain patterns**. Divine name substitution and text expansion recur on regen. Manual intervention is needed for these.
4. **The verifier is the most critical tool**. Most of the development effort went into reducing false positives without hiding real errors. The parenthetical handling alone went through four iterations.
5. **Consider a programmatic post-processor** for known LLM failure patterns (יי→ה reversion, parenthesis preservation) rather than relying on prompt instructions the model ignores.
