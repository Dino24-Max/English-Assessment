"""
Playwright E2E test: Complete assessment and verify results page shows correct scores.
Requires: pip install playwright && playwright install chromium
Run with: pytest src/test/integration/test_results_frontend.py -m e2e -v
"""
import asyncio
import sys
from pathlib import Path

import pytest

# Add project to path (test file is in src/test/integration/)
_test_file = Path(__file__).resolve()
project_root = _test_file.parent.parent.parent.parent
python_src = project_root / "src" / "main" / "python"
if str(python_src) not in sys.path:
    sys.path.insert(0, str(python_src))


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_results_frontend_displays_scores():
    """Complete assessment via browser and verify results page shows non-zero scores."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        pytest.skip("Playwright not installed: pip install playwright && playwright install chromium")

    correct = {
        1: "7 PM", 2: "8254", 3: "Deck 12", 4: "7:00", 5: "8", 6: "9173",
        7: "May", 8: "has", 9: "direct", 10: "on",
        11: '{"Bridge":"Ship\'s control center","Gangway":"Ship\'s walkway to shore","Tender":"Small boat for shore trips","Muster":"Emergency assembly"}',
        12: '{"Concierge":"Guest services specialist","Amenities":"Hotel facilities","Excursion":"Shore activities","Embark":"To board the ship"}',
        13: '{"Maitre d\'":"Restaurant manager","Sous chef":"Assistant head chef","Sommelier":"Wine expert","Steward":"Cabin attendant"}',
        14: '{"Port":"Left side of ship","Starboard":"Right side of ship","Bow":"Front of ship","Stern":"Back of ship"}',
        15: '{"Embarkation":"Boarding process","Disembarkation":"Leaving the ship","Muster":"Emergency drill","Port of call":"Stop destination"}',
        16: "Contact the Port Agent", 17: "1:00 AM", 18: "Reservations", 19: "5:00 PM", 20: "Wait at the port",
        21: "recorded_3.5s|Hello, I would like to book a table for four people at seven PM tonight, please."
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/question/1", wait_until="networkidle", timeout=15000)
            if "Assessment not found" in await page.content():
                pytest.fail("Redirected or no assessment - server may not be running")

            for q in range(1, 22):
                if q > 1:
                    await page.goto(f"http://127.0.0.1:8000/question/{q}", wait_until="networkidle", timeout=15000)
                opts = await page.locator('input[type="radio"], button.term-item, button.drop-zone, input[type="text"]').all()
                if opts:
                    await opts[0].click()
                submit = page.locator('button:has-text("Continue"), button:has-text("Submit"), #submitBtn')
                if await submit.count():
                    await submit.first.click()
                else:
                    await page.evaluate(f'''
                        fetch("/submit", {{method:"POST", body: new URLSearchParams({{question_num:{q}, answer:"{correct.get(q, "x").replace('"', '\\"')}}})}});
                    ''')
                await page.wait_for_timeout(500)

            await page.goto("http://127.0.0.1:8000/results", wait_until="networkidle", timeout=15000)
            await page.wait_for_timeout(2000)

            scores = await page.locator(".module-score").all_text_contents()
            nz = sum(1 for s in scores if s and "/" in s and int(s.split("/")[0]) > 0)
            assert nz > 0, f"All scores are 0. Module scores: {scores}"
        finally:
            await browser.close()
