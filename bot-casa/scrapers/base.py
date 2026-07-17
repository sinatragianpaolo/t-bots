from dataclasses import dataclass
from typing import Optional


@dataclass
class Listing:
    id: str
    source: str
    url: str
    title: str = ""
    price: Optional[int] = None
    rooms: Optional[int] = None
    size_sqm: Optional[int] = None
    address: Optional[str] = None
    image_url: Optional[str] = None
