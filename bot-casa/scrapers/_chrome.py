import logging
from pathlib import Path

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# Populated by scripts/solve_captcha.py via a manual, headed run on a real
# machine. Mounted as a volume in docker-compose.yml so the headless scraper
# can reuse the trust/session established there. Real Chrome (not a patched
# engine) is used because immobiliare.it's anti-bot (DataDome) hard-blocks
# known automation-browser fingerprints outright, without offering a captcha.
PROFILE_DIR = Path(__file__).resolve().parent.parent / "browser_profile_chrome"

_LAUNCH_ARGS = ["--disable-blink-features=AutomationControlled"]


async def get_html(url: str, timeout_ms: int = 60000) -> str | None:
    if not PROFILE_DIR.exists():
        logger.warning("[Chrome] no saved profile — run scripts/solve_captcha.py locally first")
        return None

    try:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                channel="chrome",
                headless=True,
                args=_LAUNCH_ARGS,
                ignore_default_args=["--enable-automation", "--no-sandbox"],
            )
            try:
                pages = context.pages
                page = pages[0] if pages else await context.new_page()
                await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                return await page.content()
            finally:
                await context.close()
    except Exception as e:
        logger.error(f"[Chrome] request failed for {url}: {e}")
    return None
