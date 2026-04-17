# Token Analysis: Formatting Seder Kodashim

Session dates: 2026-04-14 through 2026-04-16

## Summary

Formatting 11 masechot of Seder Kodashim hit Claude rate limits repeatedly. The root cause is that Mishnah formatting is fundamentally different from typical coding work — it's output-heavy, and Hebrew with nikkud tokenizes very inefficiently.

## Token profile: coding vs. Mishnah formatting

| | Coding | Mishnah formatting |
|---|---|---|
| **Input** | Read files, grep, git log — heavy | Style guide + WebFetch chapter text — moderate |
| **Output** | Small Edit diffs — light | Full file Write of 600-1500 lines Hebrew HTML — very heavy |
| **Ratio** | ~90% input, ~10% output | ~30% input, ~70% output |
| **Tokenization** | English/code: 1-2 tokens/word | Hebrew with nikkud: 3-6 tokens/word |

A single masechet Write (e.g. Zevachim at 1527 lines) may cost 60-80k output tokens, where a 1500-line code file would cost 20-30k.

## Phase-by-phase data

### Phase 1: First batch (11 parallel agents)

| Agent | Tokens | Result |
|-------|--------|--------|
| Chullin | 120,834 | Couldn't write (permissions) |
| Keritot | 84,737 | Couldn't write (permissions) |
| Temurah | 79,855 | Couldn't write (permissions) |
| Meilah | 67,504 | Couldn't write (permissions) |
| Kinnim | 49,655 | Couldn't write (permissions) |
| Kinnim retry | 50,087 | Couldn't write (permissions) |
| Zevachim | 91 | Rate limit |
| Menachot | 91 | Rate limit |
| Bekhorot | 332 | Rate limit |
| Arakhin | 97 | Rate limit |
| Tamid | 92 | Rate limit |
| Middot | 275 | Rate limit |
| Meilah retry | 213 | Rate limit |
| Temurah retry | 155 | Rate limit |

**Total: ~454k tokens, 0 files written.**

The 5 permission-failed agents each did full editorial work (fetching, formatting) but were denied file writes. The remaining agents hit rate limits — likely the burst of 11 simultaneous agents tripped the short-window rate cap.

### Phase 2: Direct Kinnim (main thread)

- Fetched 3 chapters via WebFetch
- Formatted and wrote directly
- ~10k tokens, 1 file written
- First draft had too-short lines (3-4 words); revised to hit ~8 word target

### Phase 3: Second batch (test-first approach)

- Tested Meilah agent first (~68k tokens, succeeded)
- Then launched 9 agents in parallel
- 4 completed fully: Keritot (~75k), Temurah (~81k), Tamid (~72k), Arakhin (~82k)
- 5 wrote files then hit limit: Menachot, Chullin, Bekhorot, Middot (all confirmed via meta tags)
- Zevachim agent failed — hit limit before writing

**Total: ~460k estimated, 9 of 10 files written.**

### Phase 4: Zevachim agent retry

- Hit rate limit immediately
- 0 files written

### Phase 5: Direct Zevachim (main thread)

- Fetched all 14 chapters in 3 batches of WebFetch calls
- Saved raw text to checkpoint files after each batch
- Wrote HTML in 3 incremental edits (ch 1-5, then 6-10, then 11-14)
- ~40k tokens, 1 file written

## Why parallel agents are especially costly here

1. **Duplicated reads**: 11 agents each read the same 3 reference files = 33 redundant reads
2. **Duplicated fetches**: 11 agents each make 3-14 WebFetch calls = 60-150 API round-trips
3. **Burst output**: 11 agents simultaneously writing 600-1500 lines Hebrew = potentially 500k+ output tokens in a burst window
4. **No shared state**: agents can't share fetched text or formatted sections

## Hebrew tokenization factor

The BPE tokenizer was trained primarily on English/code. Hebrew with nikkud (vowel points) tokenizes inefficiently:

- `שֶׁנִּזְבְּחוּ` (one word, "that were slaughtered") ≈ 4-6 tokens
- The English equivalent "slaughtered" ≈ 1-2 tokens
- A typical mishna line of 8 Hebrew words ≈ 25-40 tokens
- A typical code line of 8 tokens ≈ 8-15 tokens

This 2-3x multiplier on output means a Hebrew HTML file costs proportionally more than code of the same line count.

## Recommendations for future sedarim

1. **Work sequentially from the main thread** — no parallel agents
2. **Fetch first, format second** — save all raw text to disk (cheap input) before formatting (expensive output)
3. **Save intermediate state** — checkpoint raw text after each fetch batch so rate limits don't lose work
4. **Budget across sessions** — a seder of 11 masechot costs ~500-800k tokens. Expect to span 2-3 sessions.
5. **Largest masechot first** — do them when the rate limit window is fresh, not after smaller ones have consumed the budget
