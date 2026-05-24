"""
Small in-process rate limiter for local SaaS hardening.
Swap for Redis when deploying horizontally.
"""
from __future__ import annotations

from collections import defaultdict, deque
from time import time

from fastapi import HTTPException


_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(key: str, *, limit: int, window_seconds: int, message: str) -> None:
    now = time()
    bucket = _BUCKETS[key]
    while bucket and bucket[0] <= now - window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail=message)
    bucket.append(now)
