
# app/security.py

import hmac
import os
import time
from collections import defaultdict, deque
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Basic single-process API key and rate-limit protection.

    For multiple workers or replicas, replace the in-memory limiter
    with a shared store such as Redis.
    """

    def __init__(self, app):
        super().__init__(app)
        self.api_key = os.getenv("NEXUSAI_API_KEY", "").strip()
        self.limit = max(1, int(os.getenv("NEXUSAI_RATE_LIMIT", "60")))
        self.window_seconds = max(
            1, int(os.getenv("NEXUSAI_RATE_WINDOW_SECONDS", "60"))
        )
        self.requests = defaultdict(deque)
        self.lock = Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Public endpoints needed for health checks and API discovery.
        public_paths = {
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/metrics",
        }

        if request.method == "OPTIONS" or path in public_paths:
            return await call_next(request)

        # Protect API routes. Other non-API routes pass through.
        if not path.startswith("/api/"):
            return await call_next(request)

        # Fail closed if a key was not configured.
        if not self.api_key:
            return JSONResponse(
                status_code=503,
                content={"detail": "API authentication is not configured."},
            )

        supplied_key = request.headers.get("X-API-Key", "")
        if not hmac.compare_digest(supplied_key, self.api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid API key."},
            )

        # Use the client host as the rate-limit bucket.
        # Do not trust arbitrary forwarded headers without a trusted proxy.
        client_host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self.lock:
            bucket = self.requests[client_host]

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."},
                    headers={"Retry-After": str(self.window_seconds)},
                )

            bucket.append(now)

        return await call_next(request)
