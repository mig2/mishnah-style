# How Verification Works

`scripts/verify.py` checks that the formatted HTML files in `masechot/` faithfully reproduce the source text from Sefaria. It compares **word content** — not formatting, not nikkud, not layout.

## What it checks

For each mishna, the verifier extracts a normalized word list from both the **Sefaria source JSON** (`sefaria/{seder}/{tractate}/chapter_N.json`) and the **formatted HTML** (`masechot/{filename}.html`), then diffs them word-by-word.

Any word-level difference — an added word, a missing word, or a changed word — is reported as an error.

## What it does NOT check

- **Formatting**: line breaks, em-dashes, colons, semicolons, full stops — all editorial additions that the verifier strips before comparison.
- **Nikkud (vowel points)**: stripped entirely. The verifier doesn't check vowelization accuracy.
- **Bold/italic markup**: HTML tags are stripped. Whether a rabbi's name is bolded or a verse is italicized is not verified.
- **Line layout**: the ~8 word per line target is a style choice, not a fidelity measure.

## Normalization pipeline

Both source and HTML text go through the same normalization pipeline before comparison. The steps, in order:

### 1. Strip HTML tags

All `<b>`, `<i>`, `<br>`, and any other HTML tags are removed.

### 2. Strip markdown bold

`**` markers are removed (in case the LLM used markdown instead of HTML).

### 3. Strip em-dashes

The `—` character is replaced with a space. Em-dashes are editorial additions.

### 4. Strip quotes

All quote variants are removed:
- Hebrew gershayim: `״` (U+05F4), `׳` (U+05F3)
- ASCII quotes: `"` (U+0022), `'` (U+0027)

These are stripped because Sefaria uses ASCII quotes while the HTML uses Hebrew gershayim — both represent the same intent.

### 5. Handle parenthesized content

Sefaria uses parentheses for two purposes:

**Biblical references** — `(ויקרא ה)`, `(שם)`, `(דה"ב כח)`, `(שמות יז)`:
These are Sefaria's editorial annotations pointing to the source verse. They are **stripped entirely** from the word list. The formatted HTML may include them or not — either is acceptable.

The verifier recognizes a parenthesized group as a biblical reference if it contains any of these book names (checked after nikkud stripping): בראשית, שמות, ויקרא, במדבר, דברים, יהושע, שופטים, שמואל, מלכים, ישעיה, ירמיה, יחזקאל, הושע, יואל, עמוס, עובדיה, יונה, מיכה, נחום, חבקוק, צפניה, חגי, זכריה, מלאכי, תהלים, תהילים, משלי, איוב, שיר, רות, איכה, קהלת, אסתר, דניאל, עזרא, נחמיה, דברי הימים, דה"א, דה"ב, דהא, דהב, שם.

**Textual glosses** — `(אף הרוצה)`, `(זה הכלל)`, `(שניהן נשבעים)`:
These are words that ARE part of the mishna text but marked by Sefaria as variant readings. The parentheses are **stripped** but the **words are kept** in the word list.

### 6. Strip punctuation

All of `:`, `.`, `;`, `?`, `!`, `,` are replaced with spaces. These are editorial punctuation added during formatting.

### 7. Strip nikkud

All Unicode codepoints in the range U+0591–U+05C7 (Hebrew vowel points, cantillation marks) are removed. This leaves only consonants.

### 8. Strip surrounding punctuation from each word

Each word is stripped of leading/trailing `.:,;?!-–—'"״׳*`.

### 9. Normalize double-vav

`וו` is replaced with `ו`. This handles plene/defective spelling variants (e.g. מצוות → מצות).

### 10. Normalize divine name

`יי` is replaced with `ה`. Sefaria sometimes uses the double-yud convention (יי) for the divine name, while the formatted HTML uses ה. Both are valid representations of the same word.

### 11. Normalize final letters

Hebrew has 5 letters with special "final" forms used at the end of a word:
- כ → ך (kaf → final kaf)
- מ → ם (mem → final mem)
- נ → ן (nun → final nun)
- פ → ף (pe → final pe)
- צ → ץ (tsadi → final tsadi)

The verifier normalizes both directions:
- Final forms in non-final positions → regular (e.g. `דיןו` → `דינו`)
- Regular forms in final position → final (e.g. `לצימ` → `לציץ`)

This prevents false positives from LLM tokenization errors.

### 12. Strip colophons

If the normalized word list contains `סליק` or `הדרן`, everything from that word to the end is removed. These are scribal colophons (e.g. "סליק מסכת פאה") that Sefaria includes at the end of the last mishna of each masechet but are not part of the mishna text.

## Comparison

After normalization, the source and HTML word lists are compared using Python's `difflib.SequenceMatcher`. This produces opcodes:

- **equal**: words match (no error)
- **replace**: source has word X, HTML has word Y at the same position
- **delete**: source has words that don't appear in HTML (missing from HTML)
- **insert**: HTML has words that don't appear in source (added by LLM)

Any non-equal opcode is reported as a difference.

## Output

- **Console**: per-mishna ✓/✗ with diff details
- **JSON report** (`--report PATH`): structured data consumed by `fix.py`
- **HTML report** (`--report PATH`): styled human-readable report for browser review
- **JSON verification** (`--json PATH`): verify a fix/format output file before merging

## Known limitations

1. **Nikkud accuracy is not checked.** A word with completely wrong vowelization passes as long as the consonants match.

2. **Word order within a single diff block is not checked.** If the SequenceMatcher can't align words (e.g. heavily hallucinated text), it reports the entire block as one large replace rather than individual word changes.

3. **Parenthesized textual glosses must be present in the HTML.** If Sefaria marks a word as `(אף הרוצה)`, the verifier expects `אף הרוצה` to appear in the HTML (without parens). If the LLM dropped these words, it's reported as a MISSING error.

4. **Biblical reference stripping is heuristic.** If a parenthesized group happens to contain a book name but is actually mishna text, it will be incorrectly stripped. This is rare in practice.

5. **The divine name normalization (יי→ה) means the verifier cannot detect incorrect divine name handling.** If the source has `ה'` and the HTML has `יי`, the verifier treats them as equivalent. The fixer (`fix.py`) handles the correction separately.
