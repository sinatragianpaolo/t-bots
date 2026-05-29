import asyncio
import logging
from .base import Listing
from . import immobiliare, idealista, subito, tecnocasa

logger = logging.getLogger(__name__)

_SCRAPERS = [immobiliare, idealista, subito, tecnocasa]


async def search_all(filters: dict) -> list[Listing]:
    tasks = [s.search(filters) for s in _SCRAPERS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    listings: list[Listing] = []
    for scraper, result in zip(_SCRAPERS, results):
        if isinstance(result, Exception):
            logger.error(f"[{scraper.__name__.split('.')[-1]}] failed: {result}")
        else:
            listings.extend(result)
    return listings
