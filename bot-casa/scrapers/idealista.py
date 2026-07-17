import logging
import re

from bs4 import BeautifulSoup

from ._camoufox import get_html
from .base import Listing

logger = logging.getLogger(__name__)
SOURCE = "idealista.it"


async def search(filters: dict) -> list[Listing]:
    city = filters.get("city", "torino").lower()
    price_max = filters.get("price_max", "200000")

    url = f"https://www.idealista.it/vendita-case/{city}-{city}/?maxPrice={price_max}"

    html = await get_html(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    articles = soup.find_all("article", class_=re.compile(r"item"))
    if not articles:
        logger.warning(f"[{SOURCE}] blocked (no listing articles in response)")
        return []

    listings: list[Listing] = []
    for article in articles:
        try:
            link = article.find("a", class_=re.compile(r"item-link"))
            if not link:
                continue
            href = link.get("href", "")
            lid = href.strip("/").split("/")[-1]
            title = link.get("title") or link.get_text(strip=True)

            price_tag = article.find(class_=re.compile(r"price"))
            price = _parse_int(price_tag.get_text() if price_tag else "")
            rooms, sqm = _parse_details(article.find_all(class_=re.compile(r"item-detail")))

            listings.append(Listing(
                id=f"idealista-{lid}",
                source=SOURCE,
                url=f"https://www.idealista.it{href}",
                title=title,
                price=price,
                rooms=rooms,
                size_sqm=sqm,
            ))
        except Exception as e:
            logger.warning(f"[{SOURCE}] item parse error: {e}")

    return listings


def _parse_int(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", str(text))
    return int(digits) if digits else None


def _parse_details(items) -> tuple[int | None, int | None]:
    rooms, sqm = None, None
    for item in items:
        text = item.get_text(strip=True).lower()
        if any(k in text for k in ("local", "stanz", "vani")):
            m = re.search(r"(\d+)", text)
            if m:
                rooms = int(m.group(1))
        elif "m²" in text or "mq" in text:
            m = re.search(r"(\d+)", text)
            if m:
                sqm = int(m.group(1))
    return rooms, sqm
