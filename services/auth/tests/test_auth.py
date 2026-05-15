"""Tests for the auth service endpoints."""
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_USER = {"username": "alice", "password": "securepassword"}


def _register(client: TestClient, payload: dict | None = None) -> dict:
    payload = payload or _VALID_USER
    return client.post("/register", json=payload)


def _login(client: TestClient, payload: dict | None = None) -> dict:
    payload = payload or _VALID_USER
    return client.post("/login", json=payload)


def _auth_header(client: TestClient) -> dict[str, str]:
    _register(client)
    token = _login(client).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------


def test_register_success(client: TestClient) -> None:
    """A valid registration returns 201 with the user profile."""
    r = _register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == _VALID_USER["username"]
    assert body["reputation"] == 0
    assert "id" in body
    assert "password_hash" not in body
    assert "password" not in body


def test_register_duplicate_username_returns_409(client: TestClient) -> None:
    """Registering with an already-taken username returns 409."""
    _register(client)
    r = _register(client)
    assert r.status_code == 409
    assert "already taken" in r.json()["detail"]


def test_register_username_too_short_returns_422(client: TestClient) -> None:
    """Username shorter than 3 characters fails Pydantic validation."""
    r = _register(client, {"username": "ab", "password": "securepassword"})
    assert r.status_code == 422


def test_register_username_invalid_chars_returns_422(client: TestClient) -> None:
    """Username with invalid characters fails Pydantic validation."""
    r = _register(client, {"username": "alice!", "password": "securepassword"})
    assert r.status_code == 422


def test_register_password_too_short_returns_422(client: TestClient) -> None:
    """Password shorter than 8 characters fails Pydantic validation."""
    r = _register(client, {"username": "alice", "password": "short"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------


def test_login_success(client: TestClient) -> None:
    """Valid credentials return a bearer token."""
    _register(client)
    r = _login(client)
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    """Wrong password returns 401."""
    _register(client)
    r = _login(client, {"username": _VALID_USER["username"], "password": "wrongpassword"})
    assert r.status_code == 401


def test_login_unknown_user_returns_401(client: TestClient) -> None:
    """Unknown username returns 401."""
    r = _login(client, {"username": "nobody", "password": "somepassword"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------


def test_get_me_authenticated(client: TestClient) -> None:
    """Authenticated user receives their own profile."""
    headers = _auth_header(client)
    r = client.get("/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == _VALID_USER["username"]
    assert "password_hash" not in body


def test_get_me_no_token_returns_401(client: TestClient) -> None:
    """Request without a Bearer token is rejected with 401."""
    r = client.get("/me")
    assert r.status_code == 401


def test_get_me_invalid_token_returns_401(client: TestClient) -> None:
    """Request with a malformed token returns 401."""
    r = client.get("/me", headers={"Authorization": "Bearer not.a.valid.token"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /users/{username}
# ---------------------------------------------------------------------------


def test_get_public_profile_found(client: TestClient) -> None:
    """Public profile of an existing user is accessible without authentication."""
    _register(client)
    r = client.get(f"/users/{_VALID_USER['username']}")
    assert r.status_code == 200
    assert r.json()["username"] == _VALID_USER["username"]


def test_get_public_profile_not_found_returns_404(client: TestClient) -> None:
    """Non-existent username returns 404."""
    r = client.get("/users/doesnotexist")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PUT /me
# ---------------------------------------------------------------------------


def test_update_me_bio(client: TestClient) -> None:
    """Authenticated user can update their bio."""
    headers = _auth_header(client)
    r = client.put("/me", json={"bio": "Hello Agora!"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["bio"] == "Hello Agora!"


def test_update_me_unauthenticated_returns_401(client: TestClient) -> None:
    """Unauthenticated PUT /me is rejected with 401."""
    r = client.put("/me", json={"bio": "Hello"})
    assert r.status_code == 401
