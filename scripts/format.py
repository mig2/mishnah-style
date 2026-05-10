#!/usr/bin/env python3
"""Format downloaded Sefaria JSON into styled HTML using an LLM.

Usage:
    # Ollama (local)
    python3 scripts/format.py masechet Berakhot --backend ollama
    python3 scripts/format.py masechet Berakhot --backend ollama --model gemma4:31B

    # Anthropic API
    python3 scripts/format.py masechet Berakhot --backend anthropic
    python3 scripts/format.py masechet Berakhot --backend anthropic --model claude-sonnet-4-20250514

    # Claude Code headless
    python3 scripts/format.py masechet Berakhot --backend claude-code

    # Common options
    python3 scripts/format.py masechet Berakhot --chapter 3    # single chapter
    python3 scripts/format.py masechet Berakhot --dry-run      # no LLM calls

Reads raw JSON from sefaria/{seder}/{tractate}/, sends each mishna to
an LLM for editorial formatting, and assembles the result into a single
HTML file in masechot/.

Backends:
    ollama      Local Ollama instance (default: gemma3:27b on localhost:11434)
    anthropic   Anthropic Messages API (requires ANTHROPIC_API_KEY env var)
    claude-code Claude Code CLI in headless mode (requires claude on PATH)

Requires:
    - Downloaded JSON (run scripts/download.py first)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Hebrew helpers
# ---------------------------------------------------------------------------

ORDINALS = [
    "", "ראשון", "שני", "שלישי", "רביעי", "חמישי",
    "שישי", "שביעי", "שמיני", "תשיעי", "עשירי",
    "אחד עשר", "שנים עשר", "שלושה עשר", "ארבעה עשר", "חמישה עשר",
    "שישה עשר", "שבעה עשר", "שמונה עשר", "תשעה עשר", "עשרים",
    "עשרים ואחד", "עשרים ושנים", "עשרים ושלושה", "עשרים וארבעה",
    "עשרים וחמישה", "עשרים וששה", "עשרים ושבעה", "עשרים ושמונה",
    "עשרים ותשעה", "שלושים",
]


def hebrew_numeral(n):
    """Convert integer to Hebrew numeral string."""
    ones = ["", "א", "ב", "ג", "ד", "ה", "ו", "ז", "ח", "ט"]
    tens = ["", "י", "כ", "ל"]
    if n <= 0:
        return str(n)
    if n == 15:
        return "ט״ו"
    if n == 16:
        return "ט״ז"
    t, o = n // 10, n % 10
    if t > 0 and o > 0:
        return f"{tens[t]}״{ones[o]}"
    elif t > 0:
        return tens[t]
    return ones[o]


# ---------------------------------------------------------------------------
# Masechet metadata
# ---------------------------------------------------------------------------

MASECHET_FILENAMES = {
    "Berakhot": "brachot", "Peah": "peah", "Demai": "demai",
    "Kilayim": "kilayim", "Sheviit": "sheviit", "Terumot": "terumot",
    "Maasrot": "maaserot", "Maaser_Sheni": "maaser-sheni",
    "Challah": "challah", "Orlah": "orlah", "Bikkurim": "bikkurim",
    "Shabbat": "shabbat", "Eruvin": "eruvin", "Pesachim": "pesachim",
    "Shekalim": "shekalim", "Yoma": "yoma", "Sukkah": "sukkah",
    "Beitzah": "beitzah", "Rosh_Hashanah": "rosh-hashanah",
    "Taanit": "taanit", "Megillah": "megillah", "Moed_Katan": "moed-katan",
    "Chagigah": "chagigah", "Yevamot": "yevamot", "Ketubot": "ketubot",
    "Nedarim": "nedarim", "Nazir": "nazir", "Sotah": "sotah",
    "Gittin": "gittin", "Kiddushin": "kiddushin",
    "Bava_Kamma": "bava-kamma", "Bava_Metzia": "bava-metzia",
    "Bava_Batra": "bava-batra", "Sanhedrin": "sanhedrin",
    "Makkot": "makkot", "Shevuot": "shevuot", "Eduyot": "eduyot",
    "Avodah_Zarah": "avodah-zarah", "Avot": "avot", "Horayot": "horayot",
    "Zevachim": "zevachim", "Menachot": "menachot", "Chullin": "chullin",
    "Bekhorot": "bekhorot", "Arakhin": "arakhin", "Temurah": "temurah",
    "Keritot": "keritot", "Meilah": "meilah", "Tamid": "tamid",
    "Middot": "middot", "Kinnim": "kinnim", "Kelim": "keilim",
    "Ohalot": "ohalot", "Negaim": "negaim", "Parah": "parah",
    "Taharot": "taharot", "Mikvaot": "mikvaot", "Niddah": "niddah",
    "Makhshirin": "makhshirin", "Zavim": "zavim",
    "Tevul_Yom": "tevul-yom", "Yadayim": "yadayim", "Oktzin": "uktzin",
}

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from download import SEDARIM, resolve_tractate

# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def load_style_guides():
    """Load editorial guide and exemplar."""
    repo_root = Path(__file__).resolve().parent.parent
    editorial = (repo_root / "docs" / "editorial-style.md").read_text()
    exemplar_path = repo_root / ".claude" / "skills" / "mishnah" / "references" / "exemplar-zevachim-1.html"
    exemplar = exemplar_path.read_text() if exemplar_path.exists() else ""
    return editorial, exemplar


def build_system_prompt(editorial_guide, exemplar):
    """Build the system prompt sent to the LLM."""
    return f"""You are a Mishnah formatting assistant. Your job is to take raw Mishnah text and apply editorial formatting according to a precise house style.

## Rules

{editorial_guide}

## Exemplar

Study this example of correctly formatted mishna HTML (from Zevachim chapter 1):

```html
{exemplar}
```

## Your task

You will receive raw Mishnah text for a single mishna. Return ONLY the formatted content that goes inside <p class="mishna-text">...</p>. That means:
- Hebrew text with <br> line breaks
- <b> tags around rabbinic names
- <i> tags around Tanakh quotations
- Em-dashes, colons, full stops, etc. per the style guide
- NO wrapping <p> tags, NO HTML boilerplate — just the formatted text content

Do NOT alter the words of the Mishnah. Do NOT add, remove, or rephrase any words. Your job is ONLY to add formatting (line breaks, bold, italic, punctuation marks like em-dashes and colons). The Hebrew words must be reproduced exactly as given.

Respond with ONLY the formatted text. No explanations, no markdown, no code fences."""


def build_user_prompt(raw_text, perek, mishna):
    """Build the user message for a single mishna."""
    return f"Format this mishna ({hebrew_numeral(perek)}:{hebrew_numeral(mishna)}):\n\n{raw_text}"


# ---------------------------------------------------------------------------
# LLM backends
# ---------------------------------------------------------------------------

def call_ollama(system_prompt, user_prompt, model, base_url):
    """Ollama /api/chat endpoint."""
    url = f"{base_url}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 4096},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            result = json.loads(resp.read())
            return result["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama returned {e.code}: {body}")
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Cannot connect to Ollama at {base_url}: {e.reason}\n"
            "Make sure Ollama is running (ollama serve)")


def call_anthropic(system_prompt, user_prompt, model):
    """Anthropic Messages API."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Export it before running:\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...")

    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": model,
        "max_tokens": 4096,
        "temperature": 0.1,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result["content"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Anthropic API returned {e.code}: {body}")


def call_claude_code(system_prompt, user_prompt):
    """Claude Code CLI in headless mode (claude -p)."""
    combined = f"{system_prompt}\n\n---\n\n{user_prompt}"
    try:
        result = subprocess.run(
            ["claude", "-p", combined, "--output-format", "text"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"claude exited with {result.returncode}: {result.stderr}")
        return result.stdout
    except FileNotFoundError:
        raise RuntimeError(
            "claude not found on PATH. Install Claude Code:\n"
            "  npm install -g @anthropic-ai/claude-code")


# ---------------------------------------------------------------------------
# Backend dispatcher
# ---------------------------------------------------------------------------

DEFAULT_MODELS = {
    "ollama": "gemma3:27b",
    "anthropic": "claude-sonnet-4-20250514",
    "claude-code": None,  # uses whatever claude CLI defaults to
}


def call_backend(backend, system_prompt, user_prompt, model, base_url):
    """Dispatch to the chosen backend. Returns raw response text."""
    if backend == "ollama":
        return call_ollama(system_prompt, user_prompt, model, base_url)
    elif backend == "anthropic":
        return call_anthropic(system_prompt, user_prompt, model)
    elif backend == "claude-code":
        return call_claude_code(system_prompt, user_prompt)
    else:
        raise ValueError(f"Unknown backend: {backend}")


# ---------------------------------------------------------------------------
# Response cleaning
# ---------------------------------------------------------------------------

def clean_llm_response(response):
    """Strip markdown fences, wrapping tags, etc."""
    response = re.sub(r'^```(?:html)?\s*\n?', '', response, flags=re.MULTILINE)
    response = re.sub(r'\n?```\s*$', '', response, flags=re.MULTILINE)
    response = re.sub(r'^\s*<p[^>]*>\s*', '', response)
    response = re.sub(r'\s*</p>\s*$', '', response)
    return response.strip()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def strip_sefaria_html(text):
    """Remove Sefaria's inline HTML tags from raw mishna text."""
    return re.sub(r'<[^>]+>', '', text).strip()


def load_chapter_json(seder, tractate, chapter, base_dir="."):
    """Load a chapter's JSON and return list of raw mishna texts."""
    json_path = os.path.join(base_dir, "sefaria", seder.lower(), tractate.lower(),
                             f"chapter_{chapter}.json")
    if not os.path.exists(json_path):
        print(f"ERROR: {json_path} not found. Run scripts/download.py first.",
              file=sys.stderr)
        sys.exit(1)
    with open(json_path) as f:
        data = json.load(f)
    return [strip_sefaria_html(t) for t in data["versions"][0]["text"]]


def get_masechet_he(seder, tractate, base_dir="."):
    """Get Hebrew masechet name from chapter 1 JSON metadata."""
    json_path = os.path.join(base_dir, "sefaria", seder.lower(), tractate.lower(),
                             "chapter_1.json")
    with open(json_path) as f:
        data = json.load(f)
    return data.get("heTitle", "").replace("משנה ", "")


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

def count_total_mishnayot(seder, tractate, chapters, base_dir="."):
    """Count total mishnayot across all chapters to format."""
    total = 0
    for ch in chapters:
        texts = load_chapter_json(seder, tractate, ch, base_dir)
        total += len(texts)
    return total


def format_progress(done, total, start_time):
    """Return a progress string like [14/79 18% 2.3s/m ETA 2m30s]."""
    pct = (done / total * 100) if total else 0
    elapsed = time.time() - start_time
    rate = elapsed / done if done else 0
    remaining = rate * (total - done)
    mins, secs = divmod(int(remaining), 60)
    eta = f"{mins}m{secs:02d}s" if mins else f"{secs}s"
    return f"[{done}/{total} {pct:.0f}% {rate:.1f}s/m ETA {eta}]"


# ---------------------------------------------------------------------------
# HTML assembly
# ---------------------------------------------------------------------------

def build_html(masechet_he, chapters_data, git_sha, today):
    """Assemble the full HTML file from formatted chapter data."""
    num_chapters = len(chapters_data)

    toc_links = []
    for i in range(1, num_chapters + 1):
        toc_links.append(f'<a href="#perek-{i}">{hebrew_numeral(i)}</a>')
    toc = ' <span class="sep">·</span> '.join(toc_links)

    pereks_html = []
    for ch_num, mishnayot in enumerate(chapters_data, 1):
        ordinal = ORDINALS[ch_num] if ch_num < len(ORDINALS) else str(ch_num)
        mishna_divs = []
        for m_num, formatted_text in enumerate(mishnayot, 1):
            label = f"{hebrew_numeral(ch_num)}:{hebrew_numeral(m_num)}"
            mishna_divs.append(f"""  <div class="mishna" id="m{ch_num}-{m_num}">
    <p class="mishna-label"><a id="mishna-{ch_num}-{m_num}"></a><b>{label}</b></p>
    <p class="mishna-text">
      {formatted_text}
    </p>
  </div>""")

        pereks_html.append(f"""<div class="perek" id="perek{ch_num}">
  <h2 class="perek-title"><a id="perek-{ch_num}"></a>פרק {ordinal}</h2>

{"".join(chr(10) + chr(10) + m for m in mishna_divs)}

</div>""")

    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="mishnah-style-version" content="{git_sha}">
  <meta name="formatted-date" content="{today}">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>מסכת {masechet_he}</title>
  <style>
    body {{
      font-family: "SBL Hebrew", "Frank Ruehl CLM", "Ezra SIL", "David CLM",
                   "Noto Serif Hebrew", "Times New Roman", serif;
      font-size: 1.2rem;
      line-height: 2;
      max-width: 42em;
      margin: 2em auto;
      padding: 0 1.5em;
      background: #fdfdfa;
      color: #1a1a1a;
    }}

    h1.masechet-title {{
      text-align: center;
      font-size: 2rem;
      margin-bottom: 0.3em;
    }}

    nav.toc {{
      text-align: center;
      margin-bottom: 2em;
      font-size: 1.15rem;
      letter-spacing: 0.15em;
    }}
    nav.toc a {{
      color: #2a5a8a;
      text-decoration: none;
      margin: 0 0.15em;
    }}
    nav.toc a:hover {{
      text-decoration: underline;
    }}
    nav.toc .sep {{
      color: #999;
      margin: 0 0.05em;
    }}

    .perek {{
      margin-bottom: 2.5em;
    }}
    h2.perek-title {{
      font-size: 1.5rem;
      margin-bottom: 0.8em;
      border-bottom: 1px solid #ccc;
      padding-bottom: 0.3em;
    }}

    .mishna {{
      margin-bottom: 1.5em;
    }}
    .mishna-label {{
      font-size: 1.05rem;
      margin-bottom: 0.2em;
    }}
    .mishna-text {{
      margin: 0;
    }}
  </style>
</head>
<body>

<h1 class="masechet-title"><a id="top"></a>מסכת {masechet_he}</h1>

<nav class="toc">
  {toc}
</nav>

{chr(10).join(pereks_html)}

</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Format Sefaria JSON into styled Mishnah HTML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""backends:
  ollama       Local Ollama instance (default model: gemma3:27b)
  anthropic    Anthropic Messages API (default model: claude-sonnet-4-20250514)
  claude-code  Claude Code CLI headless mode (uses CLI default model)""")
    parser.add_argument("scope", choices=["masechet"],
                        help="What to format")
    parser.add_argument("name", help="Tractate name")
    parser.add_argument("--ref", default=None,
                        help="Limit scope: chapter number (e.g. 3) or "
                             "chapter:mishna (e.g. 3:5)")
    parser.add_argument("--backend", choices=["ollama", "anthropic", "claude-code"],
                        default="ollama", help="LLM backend (default: ollama)")
    parser.add_argument("--model", default=None,
                        help="Model name (default depends on backend)")
    parser.add_argument("--base-url", default="http://localhost:11434",
                        help="Ollama API base URL (ollama backend only)")
    parser.add_argument("--dir", default=".", help="Base directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print raw text, no LLM calls")
    args = parser.parse_args()

    # Resolve model default
    model = args.model or DEFAULT_MODELS[args.backend]

    result = resolve_tractate(args.name)
    if not result:
        print(f"Unknown tractate: {args.name}", file=sys.stderr)
        sys.exit(1)
    seder, tractate, num_chapters = result

    # Parse --ref
    ref_chapter = None
    ref_mishna = None
    if args.ref:
        if ':' in args.ref:
            parts = args.ref.split(':')
            ref_chapter = int(parts[0])
            ref_mishna = int(parts[1])
        else:
            ref_chapter = int(args.ref)
    chapters = [ref_chapter] if ref_chapter else list(range(1, num_chapters + 1))

    # Load style context
    editorial_guide, exemplar = load_style_guides()
    system_prompt = build_system_prompt(editorial_guide, exemplar)

    # Pre-flight checks
    if args.backend == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set. Export it before running:\n"
              "  export ANTHROPIC_API_KEY=sk-ant-...", file=sys.stderr)
        sys.exit(1)
    if args.backend == "claude-code":
        try:
            subprocess.run(["claude", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("ERROR: claude not found on PATH. Install Claude Code:\n"
                  "  npm install -g @anthropic-ai/claude-code", file=sys.stderr)
            sys.exit(1)

    masechet_he = get_masechet_he(seder, tractate, args.dir)
    if ref_mishna:
        total = 1
    else:
        total = count_total_mishnayot(seder, tractate, chapters, args.dir)

    print(f"Formatting {tractate} ({masechet_he})")
    scope_desc = args.ref if args.ref else f"chapters {chapters[0]}-{chapters[-1]}"
    print(f"  {scope_desc}, {total} mishnayot")
    print(f"  Backend: {args.backend}" +
          (f", model: {model}" if model else ""))

    done = 0
    start_time = time.time()
    all_chapters = []

    for ch in chapters:
        raw_mishnayot = load_chapter_json(seder, tractate, ch, args.dir)
        print(f"\n  Chapter {ch} ({len(raw_mishnayot)} mishnayot)")

        formatted_mishnayot = []
        for m_idx, raw_text in enumerate(raw_mishnayot, 1):
            label = f"{hebrew_numeral(ch)}:{hebrew_numeral(m_idx)}"

            # Skip mishnayot outside --ref scope
            if ref_mishna and m_idx != ref_mishna:
                formatted_mishnayot.append(None)  # placeholder
                continue

            if args.dry_run:
                print(f"    {label}: {raw_text[:60]}...")
                formatted_mishnayot.append(raw_text)
                done += 1
                continue

            progress = format_progress(done, total, start_time) if done > 0 else ""
            print(f"    {label} {progress}...", end=" ", flush=True)

            try:
                response = call_backend(args.backend, system_prompt,
                                        build_user_prompt(raw_text, ch, m_idx),
                                        model, args.base_url)
                formatted = clean_llm_response(response)
                formatted_mishnayot.append(formatted)
                done += 1
                print("✓")
            except RuntimeError as e:
                print(f"✗\n    ERROR: {e}", file=sys.stderr)
                formatted_mishnayot.append(raw_text)  # fallback to raw
                done += 1

        all_chapters.append(formatted_mishnayot)

    elapsed = time.time() - start_time

    if args.dry_run:
        print("\nDry run complete — no output generated.")
        return

    # Single-mishna mode: output just the formatted text fragment
    if ref_mishna:
        formatted_texts = [t for t in all_chapters[0] if t is not None]
        if formatted_texts:
            filename = MASECHET_FILENAMES.get(tractate, tractate.lower())
            out_dir = os.path.join(args.dir, "output")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir,
                                    f"{filename}_{ref_chapter}_{ref_mishna}.txt")
            with open(out_path, "w") as f:
                f.write(formatted_texts[0])

            mins, secs = divmod(int(elapsed), 60)
            print(f"\nDone in {mins}m{secs:02d}s")
            print(f"  Written: {out_path}")
        return

    # Full/chapter mode: assemble complete HTML
    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=args.dir, text=True
        ).strip()
    except Exception:
        git_sha = "unknown"

    # Filter out None placeholders (shouldn't happen in full mode, but safe)
    clean_chapters = []
    for ch_data in all_chapters:
        clean_chapters.append([t for t in ch_data if t is not None])

    html = build_html(masechet_he, clean_chapters, git_sha, date.today().isoformat())

    filename = MASECHET_FILENAMES.get(tractate, tractate.lower())
    out_dir = os.path.join(args.dir, "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{filename}.html")
    with open(out_path, "w") as f:
        f.write(html)

    total_mishnayot = sum(len(ch) for ch in clean_chapters)
    mins, secs = divmod(int(elapsed), 60)
    print(f"\nDone in {mins}m{secs:02d}s")
    print(f"  {len(clean_chapters)} chapters, {total_mishnayot} mishnayot")
    print(f"  Written: {out_path}")


if __name__ == "__main__":
    main()
