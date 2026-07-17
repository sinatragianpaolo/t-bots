import json
import logging
import re

from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

from .base import Listing

logger = logging.getLogger(__name__)
SOURCE = "subito.it"

_REGION_MAP: dict[str, str] = {
    "torino": "piemonte",
    "milano": "lombardia",
    "roma": "lazio",
    "napoli": "campania",
    "bologna": "emilia-romagna",
    "firenze": "toscana",
    "genova": "liguria",
    "venezia": "veneto",
}


async def search(filters: dict) -> list[Listing]:
    city = filters.get("city", "torino").lower()
    price_max = filters.get("price_max", "200000")
    rooms_min = int(filters.get("rooms_min", "2"))
    region = _REGION_MAP.get(city, city)

    url = f"https://www.subito.it/annunci-{region}/vendita/immobili/{city}/"
    params = {"pe": price_max}  # price end (max)

    async with AsyncSession() as session:
        resp = await session.get(
            url,
            params=params,
            impersonate="chrome124",
            timeout=30,
        )
        if resp.status_code != 200:
            logger.warning(f"[{SOURCE}] returned {resp.status_code}")
            return []

    return _parse(resp.text, price_max=int(price_max), rooms_min=rooms_min)


def _parse(html: str, price_max: int, rooms_min: int) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")
    script = soup.find("script", id="__NEXT_DATA__")
    if script:
        try:
            data = json.loads(script.string)
            ads = _find_key(data, "ads")
            if ads:
                return _parse_ads(ads, price_max, rooms_min)
        except Exception as e:
            logger.warning(f"[{SOURCE}] __NEXT_DATA__ parse failed: {e}")

    return _parse_html_cards(soup, price_max)


def _parse_ads(ads: list, price_max: int, rooms_min: int) -> list[Listing]:
    listings: list[Listing] = []
    for item in ads:
        try:
            lid = str(item.get("urn") or item.get("id") or "")
            listing_url = (item.get("urls") or {}).get("default", "")
            if not listing_url:
                continue

            features = {
                f["uri"]: (f.get("values") or [{}])[0].get("key", "")
                for f in item.get("features", [])
            }
            price = _parse_int(features.get("/price", ""))
            if price and price > price_max:
                continue

            listings.append(Listing(
                id=f"subito-{lid}",
                source=SOURCE,
                url=listing_url,
                title=item.get("subject", ""),
                price=price,
                address=(item.get("geo") or {}).get("city", {}).get("value"),
            ))
        except Exception as e:
            logger.warning(f"[{SOURCE}] ad parse error: {e}")
    return listings


def _parse_html_cards(soup: BeautifulSoup, price_max: int) -> list[Listing]:
    cards = soup.find_all(class_=re.compile(r"item-card|ad-card|listing"))
    listings: list[Listing] = []
    for card in cards:
        try:
            link = card.find("a", href=True)
            if not link:
                continue
            href: str = link["href"]
            lid = href.strip("/").split("-")[-1].replace(".htm", "")
            price = _parse_int(card.find(class_=re.compile(r"price")).get_text() if card.find(class_=re.compile(r"price")) else "")
            listings.append(Listing(
                id=f"subito-{lid}",
                source=SOURCE,
                url=href if href.startswith("http") else f"https://www.subito.it{href}",
                price=price,
            ))
        except Exception as e:
            logger.warning(f"[{SOURCE}] card parse error: {e}")
    return listings


def _find_key(node, key: str, depth: int = 0) -> list:
    if depth > 6:
        return []
    if isinstance(node, dict):
        if key in node and isinstance(node[key], list):
            return node[key]
        for v in node.values():
            r = _find_key(v, key, depth + 1)
            if r:
                return r
    elif isinstance(node, list):
        for item in node:
            r = _find_key(item, key, depth + 1)
            if r:
                return r
    return []


def _parse_int(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", str(text))
    return int(digits) if digits else None
