from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.dependencies import decode_token

# Routes accessibles sans aucune validation, même si un token est fourni :
# le health check et les points d'entrée non authentifiés de l'auth service.
_BYPASS_PATHS = {"/health", "/api/auth/login", "/api/auth/register"}

_INVALID_HEADER = JSONResponse(
    status_code=401,
    content={"detail": "Invalid authorization header"},
    headers={"WWW-Authenticate": "Bearer"},
)

_INVALID_TOKEN = JSONResponse(
    status_code=401,
    content={"detail": "Invalid or expired token"},
    headers={"WWW-Authenticate": "Bearer"},
)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validate the JWT in the Authorization header, if one is present.

    The gateway does not require authentication on every route: several
    downstream endpoints (e.g. public boards) are intentionally accessible
    without a token. Instead, this middleware enforces a "validate if
    present" policy: requests without an Authorization header are forwarded
    as-is, while requests carrying a Bearer token that is malformed, invalid
    or expired are rejected with 401 before reaching any downstream service.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Reject requests with an invalid Bearer token, pass through otherwise.

        Args:
            request: The incoming request.
            call_next: The next handler in the middleware chain.

        Returns:
            A 401 JSON response if a Bearer token is present but invalid,
            otherwise the response produced by the rest of the chain.
        """
        if request.url.path in _BYPASS_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("authorization")
        if auth_header is None:
            return await call_next(request)

        scheme, _, token = auth_header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return _INVALID_HEADER

        if decode_token(token) is None:
            return _INVALID_TOKEN

        return await call_next(request)
