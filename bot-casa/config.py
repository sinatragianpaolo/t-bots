import os

DEFAULT_FILTERS = {
    "city": os.getenv("FILTER_CITY", "torino"),
    "price_max": os.getenv("FILTER_PRICE_MAX", "200000"),
    "rooms_min": os.getenv("FILTER_ROOMS_MIN", "2"),
}
