import json
import logging

from bs4 import BeautifulSoup

from ._chrome import get_html
from .base import Listing

logger = logging.getLogger(__name__)
SOURCE = "immobiliare.it"


class BlockedError(Exception):
    """Raised when immobiliare.it's anti-bot check blocks the request."""


async def search(filters: dict) -> list[Listing]:
    city = filters.get("city", "torino").lower()
    price_max = filters.get("price_max", "200000")
    rooms_min = int(filters.get("rooms_min", "2"))

    parts = [f"prezzoMassimo={price_max}", "noAste=1"]
    for r in range(rooms_min, min(rooms_min + 2, 6)):
        parts.append(f"numLocali[]={r}")
    url = f"https://www.immobiliare.it/vendita-case/{city}/?{'&'.join(parts)}"

    html = await get_html(url)
    if not html:
        return []

    if "__NEXT_DATA__" not in html:
        raise BlockedError("no __NEXT_DATA__ in response — anti-bot check likely triggered")

    soup = BeautifulSoup(html, "lxml")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script:
        return []

    data = json.loads(script.string)
    raw: list[dict] = []
    try:
        for query in data["props"]["pageProps"]["dehydratedState"]["queries"]:
            try:
                items = query["state"]["data"]["results"]
                if isinstance(items, list):
                    raw.extend(items)
            except (KeyError, TypeError):
                continue
    except (KeyError, TypeError) as e:
        logger.error(f"[{SOURCE}] JSON navigation failed: {e}")
        return []

    listings: list[Listing] = []
    for item in raw:
        try:
            re_data = item.get("realEstate", {})
            lid = str(re_data.get("id", ""))
            if not lid:
                continue
            props = re_data.get("properties") or [{}]
            prop = props[0]
            price_data = prop.get("price", {})
            price = price_data.get("value") if isinstance(price_data, dict) else None
            listings.append(Listing(
                id=f"immobiliare-{lid}",
                source=SOURCE,
                url=f"https://www.immobiliare.it/annunci/{lid}/",
                title=re_data.get("title", ""),
                price=int(price) if price else None,
                rooms=prop.get("rooms"),
                size_sqm=prop.get("surface"),
                address=(prop.get("location") or {}).get("address"),
                image_url=_first_photo(re_data),
            ))
        except Exception as e:
            logger.warning(f"[{SOURCE}] item parse error: {e}")

    return listings


def _first_photo(re_data: dict) -> str | None:
    try:
        photos = re_data["multimedia"]["photos"]
        urls = photos[0]["urls"]
        return urls.get("medium") or urls.get("small")
    except (KeyError, IndexError, TypeError):
        return None
