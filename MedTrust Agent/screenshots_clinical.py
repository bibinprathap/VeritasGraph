"""Playwright capture for the CIS-themed MedTrust dashboard (alternate theme).

Verifies the governed behaviors render in the clinical theme and saves
paper-ready PNGs into ``medtrust/screenshots/`` under the ``cis_`` prefix.

Run (server must be up on :8410):
    /home/sijo/VeritasGraph/.venv/bin/uvicorn medtrust.web_clinical:app --port 8410 &
    /home/sijo/VeritasGraph/.venv/bin/python medtrust/screenshots_clinical.py
"""

from __future__ import annotations

import os
import sys

from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("MEDTRUST_CIS_URL", "http://127.0.0.1:8410")
OUT = os.path.join(os.path.dirname(__file__), "screenshots")


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    checks = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 940},
                                device_scale_factor=2)
        page.goto(BASE, wait_until="networkidle")

        expect(page.get_by_test_id("audit-valid")).to_contain_text("VERIFIED"); checks += 1
        expect(page.get_by_test_id("register")).to_contain_text("APPROVED"); checks += 1
        expect(page.get_by_test_id("register")).to_contain_text("DENIED"); checks += 1
        expect(page.get_by_test_id("register")).to_contain_text("STEP-UP"); checks += 1
        expect(page.get_by_test_id("register")).to_contain_text("AUTHORIZED"); checks += 1

        page.screenshot(path=os.path.join(OUT, "fig7_cis_dashboard_full.png"), full_page=True)
        page.get_by_test_id("register").screenshot(
            path=os.path.join(OUT, "fig8_cis_request_register.png"))
        page.get_by_test_id("kpis").screenshot(
            path=os.path.join(OUT, "fig9_cis_session_metrics.png"))
        page.get_by_test_id("audit-valid").screenshot(
            path=os.path.join(OUT, "fig10_cis_audit_verified.png"))

        browser.close()

    print(f"CIS theme checks passed: {checks}/5")
    for f in sorted(os.listdir(OUT)):
        if f.startswith("fig7") or f.startswith("fig8") or f.startswith("fig9") or f.startswith("fig10"):
            print("  -", f)
    return 0 if checks == 5 else 1


if __name__ == "__main__":
    sys.exit(main())
