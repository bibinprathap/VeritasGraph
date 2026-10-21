"""Playwright test + screenshot capture for the MedTrust dashboard.

Drives the running dashboard (http://127.0.0.1:8400), asserts the governed
behaviors are visible, and saves paper-ready PNG screenshots into
``medtrust/screenshots/``.

Run (server must be up on :8400):
    /home/sijo/VeritasGraph/.venv/bin/python medtrust/screenshots.py
"""

from __future__ import annotations

import os
import sys

from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("MEDTRUST_URL", "http://127.0.0.1:8400")
OUT = os.path.join(os.path.dirname(__file__), "screenshots")


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    checks_passed = 0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000},
                                device_scale_factor=2)
        page.goto(BASE, wait_until="networkidle")

        # --- Assertions (this is the "test") ---
        expect(page.get_by_test_id("audit-valid")).to_contain_text("valid: True")
        checks_passed += 1

        expect(page.get_by_test_id("card-clinician-lit")).to_contain_text("APPROVED")
        expect(page.get_by_test_id("card-clinician-lit")).to_contain_text("pubmed_001")
        checks_passed += 1

        expect(page.get_by_test_id("card-guest-denied")).to_contain_text("DENIED")
        checks_passed += 1

        expect(page.get_by_test_id("card-analyst-stepup")).to_contain_text("ESCALATED")
        checks_passed += 1

        expect(page.get_by_test_id("card-stepup")).to_contain_text("APPROVED")
        checks_passed += 1

        # --- Screenshots for the paper ---
        page.screenshot(path=os.path.join(OUT, "fig1_dashboard_full.png"), full_page=True)
        page.get_by_test_id("kpis").screenshot(
            path=os.path.join(OUT, "fig2_observability_kpis.png"))
        page.get_by_test_id("card-clinician-lit").screenshot(
            path=os.path.join(OUT, "fig3_approved_with_citations.png"))
        page.get_by_test_id("card-guest-denied").screenshot(
            path=os.path.join(OUT, "fig4_zero_trust_denied.png"))
        page.get_by_test_id("card-analyst-stepup").screenshot(
            path=os.path.join(OUT, "fig5_stepup_required.png"))
        page.get_by_test_id("card-stepup").screenshot(
            path=os.path.join(OUT, "fig6_stepup_approved.png"))

        browser.close()

    print(f"Playwright checks passed: {checks_passed}/5")
    print(f"Screenshots written to: {OUT}")
    for f in sorted(os.listdir(OUT)):
        print("  -", f)
    return 0 if checks_passed == 5 else 1


if __name__ == "__main__":
    sys.exit(main())
