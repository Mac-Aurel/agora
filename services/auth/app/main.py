from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth as auth_router


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
    title="Agora — Auth Service",
    description="Authentication and user management for the Agora platform.",
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

app.include_router(auth_router.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Service status and name.
    """
    return {"status": "ok", "service": "auth"}
