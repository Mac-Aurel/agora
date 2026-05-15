"""Test configuration and fixtures for the auth service.

Uses an in-memory SQLite database with StaticPool so every connection
shares the same in-memory store, enabling test isolation via
create_all / drop_all around each test.
"""
import os

# Variables d'environnement à définir AVANT tout import de l'application,
# car app.config.Settings() est instancié au niveau module lors de l'import.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRE_DAYS"] = "7"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.dependencies import get_db
from app.main import app
from app.models.user import Base

_TEST_DATABASE_URL = "sqlite:///:memory:"

# StaticPool garantit que toutes les connexions partagent la même base en mémoire.
_engine = create_engine(
    _TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _override_get_db():
    """Dependency override: yields a session bound to the test engine."""
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _reset_db() -> None:
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def client() -> TestClient:
    """Return a synchronous TestClient for the auth FastAPI app."""
    with TestClient(app) as c:
        yield c
