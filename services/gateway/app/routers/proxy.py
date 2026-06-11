from fastapi import APIRouter, Request, Response

from app.services.proxy import forward_request

router = APIRouter()

_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


@router.api_route("/api/{service}", methods=_METHODS, include_in_schema=False)
async def proxy_root(request: Request, service: str) -> Response:
    """Forward a request targeting the root of a downstream service.

    Args:
        request: The incoming gateway request.
        service: The service name extracted from `/api/{service}`.

    Returns:
        The downstream service's response.
    """
    return await forward_request(request, service, "")


@router.api_route(
    "/api/{service}/{path:path}", methods=_METHODS, include_in_schema=False
)
async def proxy_path(request: Request, service: str, path: str) -> Response:
    """Forward a request targeting a sub-path of a downstream service.

    Args:
        request: The incoming gateway request.
        service: The service name extracted from `/api/{service}/...`.
        path: Everything after `/api/{service}/`.

    Returns:
        The downstream service's response.
    """
    return await forward_request(request, service, path)
