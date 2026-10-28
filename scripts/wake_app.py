"""Open the live Streamlit app in a headless browser so it does not go to sleep.

Free Streamlit apps sleep after about 12 hours with no visitors. A plain HTTP
request does not count as a visit, so this uses a real browser, clicks the
wake-up button if the app is already asleep, and waits until the app renders.
Exits with code 1 if the app never loads, so the workflow run fails and
GitHub emails me.
"""

import sys

from playwright.sync_api import sync_playwright

APP_URL = "https://immigration-copilot-adazqhaecrqc8g7dujpe7h.streamlit.app/"
WAKE_BUTTON = "Yes, get this app back up!"
APP_TITLE = "Immigration Co-Pilot"
LOAD_TIMEOUT_MS = 180_000


def app_rendered(page):
    """The app runs inside an iframe, so check every frame for the title."""
    for frame in page.frames:
        try:
            if frame.get_by_text(APP_TITLE, exact=True).count() > 0:
                return True
        except Exception:
            pass
    return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(APP_URL, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(5_000)

        wake = page.get_by_role("button", name=WAKE_BUTTON)
        if wake.count() > 0:
            print("App was asleep. Waking it up.")
            wake.click()

        waited = 0
        while waited < LOAD_TIMEOUT_MS:
            if app_rendered(page):
                print("App is up.")
                browser.close()
                return 0
            page.wait_for_timeout(5_000)
            waited += 5_000

        print(f"App did not load within {LOAD_TIMEOUT_MS // 1000} seconds.")
        browser.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
