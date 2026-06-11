"""Test configuration and fixtures for the boards service.

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

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import Column, Table, Uuid, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.dependencies import get_db
from app.main import app
from app.models.board import Base

# Stub de la table `users` (propriété du service auth) afin que SQLAlchemy
# puisse résoudre les ForeignKey("users.id") des modèles boards lors de la
# création du schéma de test. En production, cette table existe déjà dans la
# base PostgreSQL partagée (migration du service auth).
Table(
    "users",
    Base.metadata,
    Column("id", Uuid(native_uuid=True), primary_key=True),
)

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
    """Return a synchronous TestClient for the boards FastAPI app."""
    with TestClient(app) as c:
        yield c


def make_token(user_id: uuid.UUID) -> str:
    """Build a JWT signed with the test secret, as the auth service would.

    Args:
        user_id: UUID to embed as the 'sub' claim.

    Returns:
        A signed JWT string.
    """
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(
        payload, os.environ["JWT_SECRET"], algorithm=os.environ["JWT_ALGORITHM"]
    )


@pytest.fixture()
def owner_id() -> uuid.UUID:
    """A random user id playing the role of a board owner."""
    return uuid.uuid4()


@pytest.fixture()
def other_id() -> uuid.UUID:
    """A random user id playing the role of another, non-owner user."""
    return uuid.uuid4()


@pytest.fixture()
def owner_headers(owner_id: uuid.UUID) -> dict[str, str]:
    """Authorization header for the board owner."""
    return {"Authorization": f"Bearer {make_token(owner_id)}"}


@pytest.fixture()
def other_headers(other_id: uuid.UUID) -> dict[str, str]:
    """Authorization header for a non-owner user."""
    return {"Authorization": f"Bearer {make_token(other_id)}"}
