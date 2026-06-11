import httpx
from fastapi import HTTPException, Request, Response

from app.config import settings

SERVICE_URLS: dict[str, str] = {
    "auth": settings.auth_service_url,
    "boards": settings.boards_service_url,
    "content": settings.content_service_url,
    "search": settings.search_service_url,
    "discovery": settings.discovery_service_url,
}

# Le service `boards` expose déjà ses routes avec le préfixe `/boards`
# (ex: /boards/{id}), alors que `auth` expose les siennes sans préfixe
# (ex: /login, /me). Pour ces services, le segment <service> de
# /api/<service>/... doit donc être conservé lors du forwarding ; pour les
# autres (et par défaut pour content/search/discovery, pas encore
# implémentés), il est retiré.
_KEEP_SERVICE_SEGMENT = {"boards"}

_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
    "host",
}


def _build_target_path(service: str, path: str) -> str:
    """Build the path forwarded to a downstream service.

    Args:
        service: The service name extracted from `/api/{service}/...`.
        path: Everything after `/api/{service}/` (may be empty).

    Returns:
        The path to use against the downstream service's base URL.
    """
    if service in _KEEP_SERVICE_SEGMENT:
        return f"/{service}/{path}" if path else f"/{service}"
    return f"/{path}" if path else "/"


def _filter_headers(headers: httpx.Headers) -> dict[str, str]:
    """Drop hop-by-hop headers that must not be blindly forwarded.

    Args:
        headers: The original request or response headers.

    Returns:
        A copy of the headers without hop-by-hop entries.
    """
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in _HOP_BY_HOP_HEADERS
    }


async def forward_request(request: Request, service: str, path: str) -> Response:
    """Forward an incoming request to the matching downstream microservice.

    Args:
        request: The incoming gateway request.
        service: The service name extracted from `/api/{service}/...`.
        path: Everything after `/api/{service}/` (may be empty).

    Returns:
        A Response mirroring the downstream service's status, headers and body.

    Raises:
        HTTPException: 404 if `service` is not a known downstream service, or
            502 if the downstream service cannot be reached.
    """
    base_url = SERVICE_URLS.get(service)
    if base_url is None:
        raise HTTPException(status_code=404, detail=f"Unknown service '{service}'")

    target_url = f"{base_url}{_build_target_path(service, path)}"
    body = await request.body()

    async with httpx.AsyncClient() as client:
        try:
            upstream_response = await client.request(
                method=request.method,
                url=target_url,
                headers=_filter_headers(request.headers),
                params=request.query_params,
                content=body,
                timeout=30.0,
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502, detail=f"Service '{service}' unavailable"
            ) from exc

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=_filter_headers(upstream_response.headers),
        media_type=upstream_response.headers.get("content-type"),
    )
