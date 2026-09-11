"""Abuse controls: per client rate limits and a cap on concurrent OCR work.

In memory, so they are per process. Fine for one container; a fleet would move this to
a shared store. Client address comes from Tailscale's X-Forwarded-For header when the
app sits behind Funnel, otherwise the socket peer.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

MAX_BATCH_ROWS = 100
MAX_BATCH_BYTES = 200 * 1024 * 1024
MAX_CONCURRENT_OCR = 2
OCR_WAIT_SECONDS = 8.0


class RateLimiter:
    """Sliding window: at most `limit` events per `window` seconds per key."""

    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._events[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


verify_limiter = RateLimiter(limit=10, window=60)
batch_limiter = RateLimiter(limit=2, window=600)
ocr_slots = threading.BoundedSemaphore(MAX_CONCURRENT_OCR)


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
