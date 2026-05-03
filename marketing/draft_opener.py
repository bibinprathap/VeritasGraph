#!/usr/bin/env python3
"""
draft_opener.py — Option 2 launch helper for VeritasGraph + VeritasReason.

For each target platform:
  1. Copies the platform-appropriate body from marketing/post_copy.md to your
     system clipboard.
  2. Opens that platform's *compose* / *new-post* page in your default browser.
  3. Waits for you to press Enter before moving to the next platform.

NO automation, NO logged-in-profile driving, NO API tokens. You paste, edit,
and click Submit yourself. This is the ToS-compliant launch flow.

Usage:
    python marketing/draft_opener.py                  # all platforms
    python marketing/draft_opener.py reddit medium    # subset
    python marketing/draft_opener.py --list           # show what's available
    python marketing/draft_opener.py --dry-run        # print bodies, don't open

Requires (Linux): xclip + xdg-open (already on your box).
On macOS: pbcopy + open. On Windows: clip + start. Auto-detected.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import textwrap
import webbrowser
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
COPY_FILE = REPO_ROOT / "marketing" / "post_copy.md"
GIF_PATH  = REPO_ROOT / "demos" / "policy-compliance" / "demo.gif"
OG_PATH   = REPO_ROOT / "marketing" / "og_card.png"
REPO_URL  = "https://github.com/bibinprathap/VeritasGraph"

# ---------------------------------------------------------------------------
# Clipboard — cross-platform, no third-party deps
# ---------------------------------------------------------------------------

def _copy_linux(text: str) -> None:
    if shutil.which("wl-copy"):
        subprocess.run(["wl-copy"], input=text.encode(), check=True)
    elif shutil.which("xclip"):
        subprocess.run(["xclip", "-selection", "clipboard"],
                       input=text.encode(), check=True)
    elif shutil.which("xsel"):
        subprocess.run(["xsel", "--clipboard", "--input"],
                       input=text.encode(), check=True)
    else:
        raise RuntimeError("Install xclip, xsel, or wl-copy for clipboard support.")

def _copy_macos(text: str) -> None:
    subprocess.run(["pbcopy"], input=text.encode(), check=True)

def _copy_windows(text: str) -> None:
    subprocess.run(["clip"], input=text.encode("utf-16le"), check=True, shell=True)

def copy_to_clipboard(text: str) -> None:
    if sys.platform.startswith("linux"):
        _copy_linux(text)
    elif sys.platform == "darwin":
        _copy_macos(text)
    elif sys.platform.startswith("win"):
        _copy_windows(text)
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")

# ---------------------------------------------------------------------------
# Parse marketing/post_copy.md into per-platform sections
# ---------------------------------------------------------------------------

def _slice_section(md: str, header_regex: str) -> str:
    """Return body between a `## …` heading matching regex and the next `## ` /eof."""
    pat = re.compile(rf"^##\s+{header_regex}.*?$", re.M | re.I)
    m = pat.search(md)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"^##\s+", md[start:], re.M)
    end = start + nxt.start() if nxt else len(md)
    body = md[start:end].strip()
    # Drop a leading "(≤ 280 chars)" type aside in parentheses on the heading line
    return body

def _strip_blockquote(text: str) -> str:
    """`> foo` → `foo`. Reddit / LinkedIn / X don't want our markdown quoting."""
    return "\n".join(re.sub(r"^>\s?", "", ln) for ln in text.splitlines()).strip()

def _extract_title_and_body(text: str) -> tuple[str, str]:
    """For HN / Reddit: pull `**Title:** …` and `**Body:**` blocks if present.

    Title may be soft-wrapped across multiple lines; capture until the first
    blank line or the next `**…:**` marker.
    """
    title = ""
    body = text
    m = re.search(r"\*\*Title:\*\*\s*(.+?)(?:\n\s*\n|\n\*\*)", text, re.S)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()
    m = re.search(r"\*\*Body[^:]*:\*\*\s*(.+)", text, re.S)
    if m:
        body = m.group(1).strip()
    return title, body

def load_copy() -> dict[str, dict]:
    if not COPY_FILE.exists():
        sys.exit(f"❌ Missing {COPY_FILE}. Run from the repo root.")
    md = COPY_FILE.read_text()

    x_body         = _strip_blockquote(_slice_section(md, r"🐦?\s*X\s*/\s*Twitter"))
    li_body        = _strip_blockquote(_slice_section(md, r"💼?\s*LinkedIn"))
    reddit_section = _slice_section(md, r"🤖?\s*Reddit")
    hn_section     = _slice_section(md, r"🟧?\s*Hacker\s*News")
    devto_section  = _slice_section(md, r"✍️?\s*Dev\.to")

    reddit_title, reddit_body = _extract_title_and_body(reddit_section)
    hn_title,     hn_body     = _extract_title_and_body(hn_section)

    # Mastodon: same as X but no character limit so include the repo link prominently
    mastodon_body = (x_body or "").strip()

    # Medium / Dev.to: build a long-form article body if section is just hooks
    longform = textwrap.dedent(f"""\
        # Stop asking RAG what your policy says. Ask it who's breaking the policy.

        Six months ago I shipped a GraphRAG bot for a finance team. Their first
        real question wasn't *"summarise the SoD policy"*. It was:

        > *"Give me the list of POs from Q3 that violate it, with the approver
        > names and the clause numbers."*

        Vector RAG can't answer that. You need three things on top:

        1. A **knowledge graph** of who-did-what — employees, POs, vendors,
           approvals.
        2. A **forward-chaining rule engine** that scans that graph against
           policy rules.
        3. **Provenance** so every finding cites the source clause.

        That's what we just open-sourced as **VeritasGraph + VeritasReason**.

        ## 30-second demo

        ```bash
        pip install veritas-reason
        veritasreason-policy-demo
        ```

        Output (synthetic ERP fixture, 4 Segregation-of-Duties rules):

        ```
        ✓ Reasoner fired. Detected 4 violation(s):
          PO         Rule    Evidence
          ---------- ------- -------------------------------------------------
          PO-2188    SOD-01  Approved & paid by emp:E118
          PO-2301    SOD-02  Requested & approved by emp:E091
          PO-2317    SOD-03  $48,750 approved by emp:E091 (role:Manager, not Director)
          PO-2402    SOD-04  Vendor V77 related to approver E140
        ```

        Every row is backed by a citation: `Procurement_Policy_2026.pdf#section-3.1`.

        ## Architecture

        ![demo]({REPO_URL}/raw/main/demos/policy-compliance/demo.gif)

        - **GraphRAG** (Microsoft) builds the entity graph from your docs +
          structured data
        - **VeritasReason** runs YAML-defined rules forward-chaining over the
          graph
        - **PROV-O** lineage on every emitted triple — full audit trail
        - **100% local**: Ollama + Llama 3.1, no data leaves your VPC

        ## Try it

        Repo: {REPO_URL}

        The rule-engine wheel is ~1 MB and has zero ML deps — `pip install
        veritas-reason`. The full GraphRAG side is opt-in via `[full]`.

        Honest feedback on the rule DSL (currently YAML, considering Rego)
        very welcome.
        """)

    return {
        "x": {
            "label": "X / Twitter",
            "url":   "https://twitter.com/intent/tweet",
            "body":  x_body,
            "note":  "≤280 chars. The intent URL pre-fills if your clipboard pastes cleanly.",
        },
        "linkedin": {
            "label": "LinkedIn",
            "url":   "https://www.linkedin.com/feed/?shareActive=true",
            "body":  li_body,
            "note":  "Paste into the share box. Add the demo.gif as media.",
        },
        "reddit-localllama": {
            "label": "Reddit r/LocalLLaMA",
            "url":   "https://www.reddit.com/r/LocalLLaMA/submit?type=TEXT",
            "body":  f"TITLE:\n{reddit_title}\n\n---\nBODY:\n{reddit_body}",
            "note":  "Title and body are both in the clipboard. Copy each separately.",
        },
        "reddit-ml": {
            "label": "Reddit r/MachineLearning",
            "url":   "https://www.reddit.com/r/MachineLearning/submit?type=TEXT",
            "body":  f"TITLE:\n[P] {reddit_title}\n\n---\nBODY:\n{reddit_body}",
            "note":  "Prefix with [P] for Project flair. Mods auto-remove un-flaired posts.",
        },
        "hackernews": {
            "label": "Hacker News (Show HN)",
            "url":   "https://news.ycombinator.com/submit",
            "body":  f"TITLE:\n{hn_title}\n\nURL:\n{REPO_URL}\n\n---\nFIRST COMMENT:\n{hn_body}",
            "note":  "Submit URL only. Paste the body as the FIRST comment after submitting.",
        },
        "producthunt": {
            "label": "Product Hunt",
            "url":   "https://www.producthunt.com/posts/new",
            "body":  textwrap.dedent(f"""\
                NAME: VeritasGraph
                TAGLINE: Open-source GraphRAG that reasons over your enterprise policies
                DESCRIPTION:
                Most RAG tools answer "what does the policy say?". VeritasGraph
                answers the inverse — "who is currently violating it?" — by
                pairing Microsoft GraphRAG with a forward-chaining rule engine
                (VeritasReason) and PROV-O lineage. Runs 100% locally on Ollama.

                30-second demo: pip install veritas-reason && veritasreason-policy-demo
                Repo: {REPO_URL}

                MEDIA: upload {GIF_PATH.relative_to(REPO_ROOT)} as the gallery
                       upload {OG_PATH.relative_to(REPO_ROOT)} as the thumbnail
                """),
            "note":  "PH requires you to be logged in as a Maker. One launch per product, ever.",
        },
        "medium": {
            "label": "Medium",
            "url":   "https://medium.com/new-story",
            "body":  longform,
            "note":  "Paste, then upload demo.gif inline where the ![demo] line is.",
        },
        "devto": {
            "label": "Dev.to",
            "url":   "https://dev.to/new",
            "body":  "---\ntitle: \"Stop asking RAG what your policy says. Ask it who's breaking the policy.\"\npublished: false\ntags: ai, opensource, llm, knowledgegraph\ncover_image: " + REPO_URL + "/raw/main/marketing/og_card.png\n---\n\n" + longform.split("\n", 1)[1],
            "note":  "Frontmatter is included. Toggle `published: true` when ready.",
        },
        "mastodon": {
            "label": "Mastodon",
            "url":   "https://mastodon.social/share?text=",
            "body":  mastodon_body + f"\n\n{REPO_URL}",
            "note":  "If you're on a different instance, change the URL to YOUR-INSTANCE/share?text=",
        },
    }

# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def open_url(url: str) -> None:
    # webbrowser.open uses BROWSER env var or xdg-open on Linux — opens in the
    # user's *current default* browser (whatever profile they have active).
    webbrowser.open_new_tab(url)

def run(targets: list[str], dry_run: bool) -> int:
    sections = load_copy()
    unknown = [t for t in targets if t not in sections]
    if unknown:
        print(f"❌ Unknown target(s): {unknown}")
        print(f"   Available: {', '.join(sections)}")
        return 2

    chosen = targets or list(sections.keys())
    print(f"\n📣 VeritasGraph launch helper — {len(chosen)} platform(s) queued\n")

    for i, key in enumerate(chosen, 1):
        s = sections[key]
        if not s["body"]:
            print(f"  [{i}/{len(chosen)}] ⚠️  {s['label']}: empty body in post_copy.md, skipping\n")
            continue

        print(f"  [{i}/{len(chosen)}] {s['label']}")
        print(f"        ↳ {s['note']}")
        print(f"        ↳ URL:  {s['url']}")
        print(f"        ↳ Body: {len(s['body'])} chars")
        if key == "x" and len(s['body']) > 280:
            print(f"        ⚠️  Body is {len(s['body']) - 280} chars over the 280 limit — trim before posting.")

        if dry_run:
            print("\n" + "─" * 72)
            print(s["body"])
            print("─" * 72 + "\n")
            continue

        try:
            copy_to_clipboard(s["body"])
            print("        ✓ Body copied to clipboard.")
        except Exception as e:
            print(f"        ✗ Clipboard copy failed: {e}")
            print("        Falling back to printing the body:\n")
            print(s["body"])

        open_url(s["url"])
        print("        ✓ Compose page opened in your default browser.\n")

        if i < len(chosen):
            input("        ⏎ Press Enter when you've submitted, to move on to the next platform... ")
            print()

    print("\n✅ Done. Nothing was auto-submitted — every post was your own click.\n")
    return 0

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Open each platform's compose page with the right body on the clipboard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python marketing/draft_opener.py
              python marketing/draft_opener.py reddit-localllama hackernews
              python marketing/draft_opener.py --list
              python marketing/draft_opener.py --dry-run medium
            """),
    )
    p.add_argument("targets", nargs="*", help="Platform keys (default: all)")
    p.add_argument("--list", action="store_true", help="List available platform keys and exit.")
    p.add_argument("--dry-run", action="store_true", help="Print bodies but don't open browser or touch clipboard.")
    args = p.parse_args(argv)

    if args.list:
        for k, v in load_copy().items():
            print(f"  {k:<22} → {v['label']}")
        return 0

    return run(args.targets, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
