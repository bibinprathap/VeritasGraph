# Policy-Compliance Demo (Chromium + Playwright)

A self-contained, browser-based animation of the **VeritasGraph + VeritasReason**
policy-compliance flow. Open in any browser, or record it to an animated GIF for
the README using the bundled Playwright script.

## Files

| File | Purpose |
|---|---|
| [index.html](index.html) | Pure-HTML/CSS/JS animation — no build step. Drives the four SoD rules from [rules/sod_policy.yaml](../../rules/sod_policy.yaml). |
| [record.py](record.py)   | Spins up a tiny static server, drives Chromium headlessly via Playwright, captures PNG frames, stitches them into [demo.gif](demo.gif) with Pillow. |
| `frames/`                | Raw screenshots from the last recording. |
| `demo.gif`               | The animated GIF embedded in the parent README. |

## Run the live demo

```bash
# any static server works; using Python's stdlib:
cd demos/policy-compliance
python -m http.server 8080
# open http://localhost:8080/index.html
```

The page animates the rule firing in ~12 s and stops on the audit-ready answer.

## Re-record the GIF

```bash
# one-time setup
/home/sijo/VeritasGraph/.venv/bin/pip install playwright Pillow
/home/sijo/VeritasGraph/.venv/bin/python -m playwright install chromium

# record
/home/sijo/VeritasGraph/.venv/bin/python demos/policy-compliance/record.py
```

This writes `demos/policy-compliance/demo.gif` (≈1 MB, 1280×720→960 wide,
~10 fps) which the [main README](../../README.md) embeds.

## Why this exists

The screencast makes the framework's core promise visible in seconds:
**a natural-language enterprise question → deterministic rule firing → an
audit-ready answer with citations to both the policy clause and the source ERP
row.** It complements the stdlib smoke test
[tests/test_policy_compliance_demo.py](../../tests/test_policy_compliance_demo.py),
which proves the same behaviour without a browser.
