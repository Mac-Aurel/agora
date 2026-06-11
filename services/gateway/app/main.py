import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.auth import JWTAuthMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import proxy as proxy_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler (startup / shutdown hooks).

    Args:
        app: The FastAPI application instance.

    Yields:
        Control to the running application.
    """
    yield


app = FastAPI(
    title="Agora — Gateway",
    description="Reverse proxy, JWT validation, rate limiting and request "
    "logging for the Agora platform.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ordre d'exécution voulu : Logging (englobe tout) -> RateLimit -> Auth -> routes.
# Starlette exécute les middlewares dans l'ordre inverse de leur ajout, donc le
# premier ajouté ici est le plus externe.
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(JWTAuthMiddleware)

app.include_router(proxy_router.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Service status and name.
    """
    return {"status": "ok", "service": "gateway"}
