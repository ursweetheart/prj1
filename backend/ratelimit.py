"""Per-client request limits for the public endpoints (chat, login, register)."""

import math
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

# ponytail: in memory, per process and per client IP; behind a reverse proxy every caller shares the proxy's IP.
# Move to Redis (and read X-Forwarded-For from a trusted proxy) when the API runs on several workers or behind one.
_hits: dict = defaultdict(deque)


def limit(name: str, count: int, seconds: int):
    """FastAPI dependency: at most `count` calls per `seconds` per client, then 429 with Retry-After."""
    def dep(request: Request):
        q = _hits[(name, request.client.host if request.client else "?")]
        now = time.monotonic()
        while q and now - q[0] > seconds:
            q.popleft()
        if len(q) >= count:
            raise HTTPException(429, "too many requests, try again later",
                                headers={"Retry-After": str(math.ceil(seconds - (now - q[0])))})
        q.append(now)
    return dep


def reset():
    _hits.clear()
