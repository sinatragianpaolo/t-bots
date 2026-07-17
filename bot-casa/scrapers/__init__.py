import asyncio
import logging
from .base import Listing
from . import immobiliare, idealista, subito, tecnocasa
from .immobiliare import BlockedError

logger = logging.getLogger(__name__)

_SCRAPERS = [immobiliare, idealista, subito, tecnocasa]


async def search_all(filters: dict) -> tuple[list[Listing], list[str]]:
    tasks = [s.search(filters) for s in _SCRAPERS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    listings: list[Listing] = []
    blocked: list[str] = []
    for scraper, result in zip(_SCRAPERS, results):
        name = scraper.__name__.split(".")[-1]
        if isinstance(result, BlockedError):
            logger.error(f"[{name}] blocked: {result}")
            blocked.append(name)
        elif isinstance(result, Exception):
            logger.error(f"[{name}] failed: {result}")
        else:
            listings.extend(result)
    return listings, blocked
