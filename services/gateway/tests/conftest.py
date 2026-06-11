import os
import uuid

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from jose import jwt

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("AUTH_SERVICE_URL", "http://auth-test")
os.environ.setdefault("BOARDS_SERVICE_URL", "http://boards-test")
os.environ.setdefault("CONTENT_SERVICE_URL", "http://content-test")
os.environ.setdefault("SEARCH_SERVICE_URL", "http://search-test")
os.environ.setdefault("DISCOVERY_SERVICE_URL", "http://discovery-test")
os.environ.setdefault("RATE_LIMIT_MAX_REQUESTS", "5")
os.environ.setdefault("RATE_LIMIT_WINDOW_SECONDS", "60")

from app import dependencies  # noqa: E402
from app.main import app  # noqa: E402

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ["JWT_ALGORITHM"]


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """Replace the shared Redis client with an in-memory fake for each test.

    Each test gets a fresh fake instance, so rate-limit counters never leak
    between tests.
    """
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(dependencies, "redis_client", fake)
    return fake


@pytest.fixture
def client():
    """A TestClient for the gateway app."""
    return TestClient(app)


def make_token(sub: str | None = None) -> str:
    """Build a signed JWT for the given (or a random) user id.

    Args:
        sub: The 'sub' claim to embed. A random UUID is used if omitted.

    Returns:
        The encoded JWT string.
    """
    payload = {"sub": sub or str(uuid.uuid4())}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def auth_headers():
    """Authorization header carrying a valid Bearer token."""
    return {"Authorization": f"Bearer {make_token()}"}
