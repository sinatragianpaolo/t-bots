import json
import logging

from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

_URL = "http://flaresolverr:8191/v1"


async def get_html(url: str, timeout_ms: int = 60000) -> str | None:
    payload = {"cmd": "request.get", "url": url, "maxTimeout": timeout_ms}
    try:
        async with AsyncSession() as session:
            resp = await session.post(
                _URL,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=timeout_ms / 1000 + 10,
            )
            data = resp.json()
            if data.get("status") == "ok":
                return data["solution"]["response"]
            logger.warning(f"[FlareSolverr] {url}: {data.get('message', 'unknown error')}")
    except Exception as e:
        logger.error(f"[FlareSolverr] request failed for {url}: {e}")
    return None
