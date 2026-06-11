from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.dependencies import get_redis_client

_EXEMPT_PATHS = {"/health"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply a global per-IP rate limit backed by Redis.

    Uses a fixed-window counter: each client IP gets a Redis key that is
    incremented on every request and expires after
    `settings.rate_limit_window_seconds`. Once the counter exceeds
    `settings.rate_limit_max_requests` within that window, further requests
    receive a 429 response until the window resets.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Increment the request counter for the client and enforce the limit.

        Args:
            request: The incoming request.
            call_next: The next handler in the middleware chain.

        Returns:
            A 429 JSON response if the limit is exceeded, otherwise the
            response produced by the rest of the chain.
        """
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        redis_client = get_redis_client()
        key = f"ratelimit:{client_host}"

        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, settings.rate_limit_window_seconds)

        if current > settings.rate_limit_max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )

        return await call_next(request)
