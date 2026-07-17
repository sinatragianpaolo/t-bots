import logging

from camoufox.async_api import AsyncCamoufox

logger = logging.getLogger(__name__)


async def get_html(url: str, timeout_ms: int = 60000) -> str | None:
    try:
        async with AsyncCamoufox(headless=True) as browser:
            page = await browser.new_page()
            await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            html = await page.content()
            return html
    except Exception as e:
        logger.error(f"[Camoufox] request failed for {url}: {e}")
    return None
