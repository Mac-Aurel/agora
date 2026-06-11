import json

import httpx
import respx

from tests.conftest import make_token


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "gateway"}


@respx.mock
def test_proxy_auth_login_strips_api_auth_prefix(client):
    route = respx.post("http://auth-test/login").mock(
        return_value=httpx.Response(200, json={"access_token": "abc"})
    )

    response = client.post(
        "/api/auth/login", json={"username": "alice", "password": "secret"}
    )

    assert response.status_code == 200
    assert response.json() == {"access_token": "abc"}
    assert route.called
    sent_request = route.calls.last.request
    assert sent_request.url.path == "/login"
    assert json.loads(sent_request.content) == {
        "username": "alice",
        "password": "secret",
    }


@respx.mock
def test_proxy_boards_root_keeps_boards_segment(client):
    route = respx.get("http://boards-test/boards").mock(
        return_value=httpx.Response(200, json=[])
    )

    response = client.get("/api/boards")

    assert response.status_code == 200
    assert response.json() == []
    assert route.called
    assert route.calls.last.request.url.path == "/boards"


@respx.mock
def test_proxy_boards_with_id_keeps_boards_segment(client):
    board_id = "11111111-1111-1111-1111-111111111111"
    route = respx.get(f"http://boards-test/boards/{board_id}").mock(
        return_value=httpx.Response(200, json={"id": board_id})
    )

    response = client.get(f"/api/boards/{board_id}")

    assert response.status_code == 200
    assert response.json() == {"id": board_id}
    assert route.called
    assert route.calls.last.request.url.path == f"/boards/{board_id}"


@respx.mock
def test_proxy_forwards_authorization_header(client, auth_headers):
    route = respx.get("http://boards-test/boards").mock(
        return_value=httpx.Response(200, json=[])
    )

    response = client.get("/api/boards", headers=auth_headers)

    assert response.status_code == 200
    sent_request = route.calls.last.request
    assert sent_request.headers["authorization"] == auth_headers["Authorization"]


def test_proxy_unknown_service_returns_404(client):
    response = client.get("/api/unknown/foo")
    assert response.status_code == 404


@respx.mock
def test_proxy_downstream_unreachable_returns_502(client):
    respx.get("http://boards-test/boards").mock(
        side_effect=httpx.ConnectError("connection refused")
    )

    response = client.get("/api/boards")

    assert response.status_code == 502


@respx.mock
def test_auth_middleware_passthrough_without_token(client):
    respx.get("http://boards-test/boards").mock(
        return_value=httpx.Response(200, json=[])
    )

    response = client.get("/api/boards")

    assert response.status_code == 200


@respx.mock
def test_auth_middleware_rejects_invalid_token(client):
    route = respx.get("http://boards-test/boards").mock(
        return_value=httpx.Response(200, json=[])
    )

    response = client.get(
        "/api/boards", headers={"Authorization": "Bearer not-a-valid-token"}
    )

    assert response.status_code == 401
    assert not route.called


@respx.mock
def test_auth_middleware_rejects_malformed_header(client):
    route = respx.get("http://boards-test/boards").mock(
        return_value=httpx.Response(200, json=[])
    )

    response = client.get("/api/boards", headers={"Authorization": "Token xyz"})

    assert response.status_code == 401
    assert not route.called


@respx.mock
def test_auth_middleware_accepts_valid_token(client, auth_headers):
    respx.get("http://boards-test/boards").mock(
        return_value=httpx.Response(200, json=[])
    )

    response = client.get("/api/boards", headers=auth_headers)

    assert response.status_code == 200


@respx.mock
def test_auth_middleware_bypasses_login_even_with_invalid_token(client):
    respx.post("http://auth-test/login").mock(
        return_value=httpx.Response(200, json={"access_token": "abc"})
    )

    response = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "secret"},
        headers={"Authorization": "Bearer not-a-valid-token"},
    )

    assert response.status_code == 200


@respx.mock
def test_auth_middleware_expired_token_rejected(client):
    expired_token = make_token()
    # Build a token that fails decoding by tampering with its signature.
    tampered = expired_token[:-1] + ("a" if expired_token[-1] != "a" else "b")

    respx.get("http://boards-test/boards").mock(
        return_value=httpx.Response(200, json=[])
    )

    response = client.get(
        "/api/boards", headers={"Authorization": f"Bearer {tampered}"}
    )

    assert response.status_code == 401


@respx.mock
def test_rate_limit_blocks_after_threshold(client):
    respx.get("http://boards-test/boards").mock(
        return_value=httpx.Response(200, json=[])
    )

    # RATE_LIMIT_MAX_REQUESTS is set to 5 in the test environment.
    for _ in range(5):
        response = client.get("/api/boards")
        assert response.status_code == 200

    response = client.get("/api/boards")
    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_rate_limit_exempts_health(client):
    for _ in range(10):
        response = client.get("/health")
        assert response.status_code == 200
