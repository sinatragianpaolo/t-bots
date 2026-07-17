"""Run locally (NOT in Docker) with a real display and a real Chrome window
to get past immobiliare.it's bot-check (DataDome) by browsing normally —
mouse movement and human timing, not clicking a captcha. Saves a Chrome
profile that the headless scraper (scrapers/_chrome.py) reuses.

Usage:
    python scripts/solve_captcha.py [url]
"""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE_DIR = Path(__file__).resolve().parent.parent / "browser_profile_chrome"
DEFAULT_URL = "https://www.immobiliare.it/vendita-case/torino/"


async def main(url: str) -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation", "--no-sandbox"],
        )
        pages = context.pages
        page = pages[0] if pages else await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")

        print("Naviga normalmente nella finestra Chrome (scrolla, muovi il mouse,")
        print("clicca su un annuncio) finché non vedi gli annunci veri, non la pagina di blocco.")
        input("Premi INVIO qui quando la pagina è sbloccata... ")

        await context.close()

    print(f"Profilo salvato in: {PROFILE_DIR}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    asyncio.run(main(target))
