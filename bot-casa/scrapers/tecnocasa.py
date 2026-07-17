import logging
import re

from curl_cffi.requests import AsyncSession

from .base import Listing

logger = logging.getLogger(__name__)
SOURCE = "tecnocasa.it"

# city ID is extracted from the search page's :search prop at first run
# format: {"city": <id>, "province": "TO", "region": "pie", "contract": "acquis", "sector": "res"}
_CITY_IDS: dict[str, int] = {
    "torino": 13800324512838,
    "milano": 2664460,
    "roma": 3169070,
}

_REGION_MAP: dict[str, str] = {
    "torino": ("TO", "pie"),
    "milano": ("MI", "lom"),
    "roma": ("RM", "laz"),
}


async def search(filters: dict) -> list[Listing]:
    city = filters.get("city", "torino").lower()
    price_max = int(filters.get("price_max", "200000"))
    rooms_min = int(filters.get("rooms_min", "2"))

    city_id = _CITY_IDS.get(city)
    if not city_id:
        logger.warning(f"[{SOURCE}] no city ID for '{city}', skipping")
        return []

    province, region = _REGION_MAP.get(city, ("", ""))

    params = {
        "city": city_id,
        "contract": "acquis",
        "province": province,
        "region": region,
        "sector": "res",
        "section": "estate",
        "page": 1,
    }

    headers = {
        "Referer": f"https://www.tecnocasa.it/annunci/immobili/{region}/{city}/{city}.html",
        "Accept": "application/json, text/plain, */*",
    }

    async with AsyncSession() as session:
        resp = await session.get(
            "https://www.tecnocasa.it/api/estates/search",
            params=params,
            headers=headers,
            impersonate="chrome124",
            timeout=30,
        )
        resp.raise_for_status()

    estates = resp.json().get("estates", [])

    listings: list[Listing] = []
    for item in estates:
        try:
            price = _parse_int(item.get("price", ""))
            if price and price > price_max:
                continue

            rooms = _parse_int(item.get("rooms_short", ""))
            if rooms and rooms < rooms_min:
                continue

            lid = str(item.get("id", ""))
            if not lid:
                continue

            listings.append(Listing(
                id=f"tecnocasa-{lid}",
                source=SOURCE,
                url=item.get("detail_url", ""),
                title=item.get("title", ""),
                price=price,
                rooms=rooms,
                size_sqm=_parse_int(item.get("surface", "")),
                address=item.get("subtitle"),
                image_url=_first_image(item),
            ))
        except Exception as e:
            logger.warning(f"[{SOURCE}] item parse error: {e}")

    return listings


def _parse_int(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", str(text))
    return int(digits) if digits else None


def _first_image(item: dict) -> str | None:
    try:
        return item["images"][0]["url"]["gallery_preview"]
    except (KeyError, IndexError, TypeError):
        return None
