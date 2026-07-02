"""HTTP middleware: request-id propagation, access logging, and a lightweight
in-process rate limiter suitable for single-node deployments (a Redis-backed
limiter can be swapped in for horizontal scaling)."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import get_logger, request_id_ctx

logger = get_logger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request id, bind it to the log context, and log the request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=elapsed_ms,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window per-client rate limiter (best-effort, in-memory)."""

    def __init__(self, app, *, limit: int = 120, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        fwd = request.headers.get("X-Forwarded-For")
        ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")
        return ip

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only throttle the API surface; skip docs/health probes.
        if not request.url.path.startswith(settings.API_V1_PREFIX):
            return await call_next(request)

        now = time.time()
        key = self._client_key(request)
        bucket = self._hits[key]
        while bucket and bucket[0] <= now - self.window:
            bucket.popleft()
        if len(bucket) >= self.limit:
            retry_after = int(self.window - (now - bucket[0])) + 1
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited", "message": "Too many requests."}},
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)
        return await call_next(request)
