import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("agora.gateway")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, response status and duration for every request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Time the request and log a summary line once it completes.

        Args:
            request: The incoming request.
            call_next: The next handler in the middleware chain.

        Returns:
            The response produced by the rest of the chain.
        """
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        client_host = request.client.host if request.client else "-"
        logger.info(
            "%s %s %s %s %.2fms",
            client_host,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
