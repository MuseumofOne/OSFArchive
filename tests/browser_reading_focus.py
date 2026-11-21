"""Browser regression for the shared explorer. Run with Playwright against a served archive."""
import argparse
from playwright.sync_api import sync_playwright


def verify(page, url):
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_selector("[data-ax-records]", state="attached")
    ids = page.locator("[data-ax-records]").evaluate("n => JSON.parse(n.textContent).slice(0, 5).map(r => r.id)")
    assert len(ids) == 5
    page.evaluate("(ids) => localStorage.setItem('museum-of-one-reading-list-v1', JSON.stringify(ids))", ids)
    page.goto(url.split("#")[0] + "#ax:view=reading", wait_until="domcontentloaded")
    page.reload(wait_until="domcontentloaded")

    rows = page.locator("[data-ax-reading] button")
    rows.nth(4).wait_for()
    for index, expected in [(3, 3), (3, 2), (2, 1), (1, 0), (0, None)]:
        before = rows.count()
        rows.nth(index).focus()
        page.keyboard.press("Enter")
        assert rows.count() == before - 1
        if expected is None:
            page.wait_for_function("document.activeElement.matches('[data-ax-panel=reading] .ax-section-head :is(h2,h3)')")
        else:
            page.wait_for_function(
                "i => document.activeElement === document.querySelectorAll('[data-ax-reading] button')[i]",
                arg=expected,
            )
    page.evaluate("(ids) => localStorage.setItem('museum-of-one-reading-list-v1', JSON.stringify(ids))", ids)
    page.reload(wait_until="domcontentloaded")
    rows.nth(4).wait_for()
    page.locator("[data-ax-clear]").focus()
    page.keyboard.press("Enter")
    page.wait_for_function("document.activeElement.matches('[data-ax-panel=reading] .ax-section-head :is(h2,h3)')")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Archive homepage or the native Ghost library URL")
    parser.add_argument("--engine", choices=["chromium", "webkit"], default="chromium")
    parser.add_argument("--width", type=int, default=1440)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = getattr(playwright, args.engine).launch()
        context = browser.new_context(viewport={"width": args.width, "height": 900})
        try:
            verify(context.new_page(), args.url)
        finally:
            browser.close()
