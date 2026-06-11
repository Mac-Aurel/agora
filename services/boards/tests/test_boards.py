"""Tests for the boards service endpoints."""

import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt

_BOARD_PAYLOAD = {
    "title": "My Board",
    "description": "A board about Agora",
    "tags": ["research", "agora"],
    "is_public": True,
}


def _create_board(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    payload = {**_BOARD_PAYLOAD, **overrides}
    r = client.post("/boards", json=payload, headers=headers)
    assert r.status_code == 201
    return r.json()


def _add_item(client: TestClient, board_id: str, headers: dict[str, str]) -> dict:
    r = client.post(
        f"/boards/{board_id}/items",
        json={"content_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()


def _contribute(
    client: TestClient, board_id: str, item_id: str, headers: dict[str, str]
) -> dict:
    r = client.post(
        f"/boards/{board_id}/items/{item_id}/contribute",
        json={"type": "comment", "body": "Great find!"},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()


# ---------------------------------------------------------------------------
# POST /boards
# ---------------------------------------------------------------------------


def test_create_board_success(client: TestClient, owner_headers: dict) -> None:
    """A valid creation returns 201 with the board, including tags and owner."""
    body = _create_board(client, owner_headers)
    assert body["title"] == _BOARD_PAYLOAD["title"]
    assert body["tags"] == _BOARD_PAYLOAD["tags"]
    assert body["is_public"] is True
    assert "id" in body
    assert "owner_id" in body


def test_create_board_unauthenticated_returns_401(client: TestClient) -> None:
    """Creating a board without a token is rejected with 401."""
    r = client.post("/boards", json=_BOARD_PAYLOAD)
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /boards
# ---------------------------------------------------------------------------


def test_list_boards_returns_only_public(
    client: TestClient, owner_headers: dict
) -> None:
    """Listing boards only returns public ones."""
    _create_board(client, owner_headers, title="Public Board", is_public=True)
    _create_board(client, owner_headers, title="Private Board", is_public=False)

    r = client.get("/boards")
    assert r.status_code == 200
    titles = [b["title"] for b in r.json()]
    assert "Public Board" in titles
    assert "Private Board" not in titles


# ---------------------------------------------------------------------------
# GET /boards/{id}
# ---------------------------------------------------------------------------


def test_get_board_public_without_auth(client: TestClient, owner_headers: dict) -> None:
    """A public board's detail is accessible without authentication and lists items."""
    board = _create_board(client, owner_headers)
    r = client.get(f"/boards/{board['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == board["id"]
    assert body["items"] == []


def test_get_board_private_owner_can_view(
    client: TestClient, owner_headers: dict
) -> None:
    """The owner can view their own private board."""
    board = _create_board(client, owner_headers, is_public=False)
    r = client.get(f"/boards/{board['id']}", headers=owner_headers)
    assert r.status_code == 200


def test_get_board_private_other_user_returns_404(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """A private board is hidden (404) from non-owner authenticated users."""
    board = _create_board(client, owner_headers, is_public=False)
    r = client.get(f"/boards/{board['id']}", headers=other_headers)
    assert r.status_code == 404


def test_get_board_private_unauthenticated_returns_404(
    client: TestClient, owner_headers: dict
) -> None:
    """A private board is hidden (404) from unauthenticated requests."""
    board = _create_board(client, owner_headers, is_public=False)
    r = client.get(f"/boards/{board['id']}")
    assert r.status_code == 404


def test_get_board_not_found(client: TestClient) -> None:
    """A non-existent board returns 404."""
    r = client.get(f"/boards/{uuid.uuid4()}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PUT /boards/{id}
# ---------------------------------------------------------------------------


def test_update_board_owner_success(client: TestClient, owner_headers: dict) -> None:
    """The owner can update their board's fields."""
    board = _create_board(client, owner_headers)
    r = client.put(
        f"/boards/{board['id']}",
        json={"title": "Updated title", "is_public": False},
        headers=owner_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Updated title"
    assert body["is_public"] is False
    # Untouched fields are preserved
    assert body["tags"] == _BOARD_PAYLOAD["tags"]


def test_update_board_non_owner_returns_403(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """A non-owner cannot update the board."""
    board = _create_board(client, owner_headers)
    r = client.put(
        f"/boards/{board['id']}", json={"title": "Hacked"}, headers=other_headers
    )
    assert r.status_code == 403


def test_update_board_not_found(client: TestClient, owner_headers: dict) -> None:
    """Updating a non-existent board returns 404."""
    r = client.put(
        f"/boards/{uuid.uuid4()}", json={"title": "X"}, headers=owner_headers
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /boards/{id}
# ---------------------------------------------------------------------------


def test_delete_board_owner_success(client: TestClient, owner_headers: dict) -> None:
    """The owner can delete their board, which then disappears."""
    board = _create_board(client, owner_headers)
    r = client.delete(f"/boards/{board['id']}", headers=owner_headers)
    assert r.status_code == 204

    r2 = client.get(f"/boards/{board['id']}")
    assert r2.status_code == 404


def test_delete_board_non_owner_returns_403(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """A non-owner cannot delete the board."""
    board = _create_board(client, owner_headers)
    r = client.delete(f"/boards/{board['id']}", headers=other_headers)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# POST /boards/{id}/items
# ---------------------------------------------------------------------------


def test_add_item_owner_success(client: TestClient, owner_headers: dict) -> None:
    """The owner can add an item to their board, validated by default."""
    board = _create_board(client, owner_headers)
    content_id = str(uuid.uuid4())
    r = client.post(
        f"/boards/{board['id']}/items",
        json={"content_id": content_id},
        headers=owner_headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["content_id"] == content_id
    assert body["board_id"] == board["id"]
    assert body["status"] == "validated"


def test_add_item_non_owner_returns_403(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """A non-owner cannot add an item directly to the board."""
    board = _create_board(client, owner_headers)
    r = client.post(
        f"/boards/{board['id']}/items",
        json={"content_id": str(uuid.uuid4())},
        headers=other_headers,
    )
    assert r.status_code == 403


def test_add_item_board_not_found(client: TestClient, owner_headers: dict) -> None:
    """Adding an item to a non-existent board returns 404."""
    r = client.post(
        f"/boards/{uuid.uuid4()}/items",
        json={"content_id": str(uuid.uuid4())},
        headers=owner_headers,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /boards/{id}/items/{item_id}
# ---------------------------------------------------------------------------


def test_remove_item_owner_success(client: TestClient, owner_headers: dict) -> None:
    """The owner can remove an item from their board."""
    board = _create_board(client, owner_headers)
    item = _add_item(client, board["id"], owner_headers)

    r = client.delete(
        f"/boards/{board['id']}/items/{item['id']}", headers=owner_headers
    )
    assert r.status_code == 204

    detail = client.get(f"/boards/{board['id']}").json()
    assert detail["items"] == []


def test_remove_item_not_found(client: TestClient, owner_headers: dict) -> None:
    """Removing a non-existent item returns 404."""
    board = _create_board(client, owner_headers)
    r = client.delete(
        f"/boards/{board['id']}/items/{uuid.uuid4()}", headers=owner_headers
    )
    assert r.status_code == 404


def test_remove_item_non_owner_returns_403(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """A non-owner cannot remove an item from the board."""
    board = _create_board(client, owner_headers)
    item = _add_item(client, board["id"], owner_headers)

    r = client.delete(
        f"/boards/{board['id']}/items/{item['id']}", headers=other_headers
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# POST /boards/{id}/items/{item_id}/contribute
# ---------------------------------------------------------------------------


def test_contribute_success(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """Any authenticated user can submit a pending contribution on a public board."""
    board = _create_board(client, owner_headers)
    item = _add_item(client, board["id"], owner_headers)

    body = _contribute(client, board["id"], item["id"], other_headers)
    assert body["status"] == "pending"
    assert body["type"] == "comment"
    assert body["body"] == "Great find!"


def test_contribute_unauthenticated_returns_401(
    client: TestClient, owner_headers: dict
) -> None:
    """Submitting a contribution without a token is rejected with 401."""
    board = _create_board(client, owner_headers)
    item = _add_item(client, board["id"], owner_headers)

    r = client.post(
        f"/boards/{board['id']}/items/{item['id']}/contribute",
        json={"type": "comment", "body": "x"},
    )
    assert r.status_code == 401


def test_contribute_item_not_found(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """Contributing to a non-existent item returns 404."""
    board = _create_board(client, owner_headers)
    r = client.post(
        f"/boards/{board['id']}/items/{uuid.uuid4()}/contribute",
        json={"type": "comment", "body": "x"},
        headers=other_headers,
    )
    assert r.status_code == 404


def test_contribute_private_board_other_user_returns_404(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """A non-owner cannot contribute to a private board (hidden as 404)."""
    board = _create_board(client, owner_headers, is_public=False)
    item = _add_item(client, board["id"], owner_headers)

    r = client.post(
        f"/boards/{board['id']}/items/{item['id']}/contribute",
        json={"type": "comment", "body": "x"},
        headers=other_headers,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /boards/{id}/contributions
# ---------------------------------------------------------------------------


def test_list_contributions_owner_success(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """The owner sees pending contributions for their board."""
    board = _create_board(client, owner_headers)
    item = _add_item(client, board["id"], owner_headers)
    _contribute(client, board["id"], item["id"], other_headers)

    r = client.get(f"/boards/{board['id']}/contributions", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["status"] == "pending"


def test_list_contributions_non_owner_returns_403(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """A non-owner cannot list pending contributions."""
    board = _create_board(client, owner_headers)
    r = client.get(f"/boards/{board['id']}/contributions", headers=other_headers)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# PUT /contributions/{id}/validate and /reject
# ---------------------------------------------------------------------------


def test_validate_contribution_success(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """The board owner can validate a pending contribution."""
    board = _create_board(client, owner_headers)
    item = _add_item(client, board["id"], owner_headers)
    contribution = _contribute(client, board["id"], item["id"], other_headers)

    r = client.put(
        f"/contributions/{contribution['id']}/validate", headers=owner_headers
    )
    assert r.status_code == 200
    assert r.json()["status"] == "validated"


def test_reject_contribution_success(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """The board owner can reject a pending contribution."""
    board = _create_board(client, owner_headers)
    item = _add_item(client, board["id"], owner_headers)
    contribution = _contribute(client, board["id"], item["id"], other_headers)

    r = client.put(f"/contributions/{contribution['id']}/reject", headers=owner_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_validate_contribution_non_owner_returns_403(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """A non-owner cannot validate a contribution."""
    board = _create_board(client, owner_headers)
    item = _add_item(client, board["id"], owner_headers)
    contribution = _contribute(client, board["id"], item["id"], other_headers)

    r = client.put(
        f"/contributions/{contribution['id']}/validate", headers=other_headers
    )
    assert r.status_code == 403


def test_validate_contribution_already_processed_returns_409(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """Validating an already-processed contribution returns 409."""
    board = _create_board(client, owner_headers)
    item = _add_item(client, board["id"], owner_headers)
    contribution = _contribute(client, board["id"], item["id"], other_headers)

    client.put(f"/contributions/{contribution['id']}/validate", headers=owner_headers)
    r = client.put(
        f"/contributions/{contribution['id']}/validate", headers=owner_headers
    )
    assert r.status_code == 409


def test_validate_contribution_not_found(
    client: TestClient, owner_headers: dict
) -> None:
    """Validating a non-existent contribution returns 404."""
    r = client.put(f"/contributions/{uuid.uuid4()}/validate", headers=owner_headers)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /boards/{id}/items/connect
# ---------------------------------------------------------------------------


def test_connect_items_success(client: TestClient, owner_headers: dict) -> None:
    """Two items of the same board can be connected with a label."""
    board = _create_board(client, owner_headers)
    item_a = _add_item(client, board["id"], owner_headers)
    item_b = _add_item(client, board["id"], owner_headers)

    r = client.post(
        f"/boards/{board['id']}/items/connect",
        json={"item_a_id": item_a["id"], "item_b_id": item_b["id"], "label": "related"},
        headers=owner_headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["item_a_id"] == item_a["id"]
    assert body["item_b_id"] == item_b["id"]
    assert body["label"] == "related"


def test_connect_items_not_in_board_returns_404(
    client: TestClient, owner_headers: dict
) -> None:
    """Connecting with an item id that doesn't belong to the board returns 404."""
    board = _create_board(client, owner_headers)
    item_a = _add_item(client, board["id"], owner_headers)

    r = client.post(
        f"/boards/{board['id']}/items/connect",
        json={"item_a_id": item_a["id"], "item_b_id": str(uuid.uuid4())},
        headers=owner_headers,
    )
    assert r.status_code == 404


def test_connect_items_unauthenticated_returns_401(
    client: TestClient, owner_headers: dict
) -> None:
    """Connecting items without a token is rejected with 401."""
    board = _create_board(client, owner_headers)
    item_a = _add_item(client, board["id"], owner_headers)
    item_b = _add_item(client, board["id"], owner_headers)

    r = client.post(
        f"/boards/{board['id']}/items/connect",
        json={"item_a_id": item_a["id"], "item_b_id": item_b["id"]},
    )
    assert r.status_code == 401


def test_connect_items_private_board_other_user_returns_404(
    client: TestClient, owner_headers: dict, other_headers: dict
) -> None:
    """A non-owner cannot create connections on a private board (hidden as 404)."""
    board = _create_board(client, owner_headers, is_public=False)
    item_a = _add_item(client, board["id"], owner_headers)
    item_b = _add_item(client, board["id"], owner_headers)

    r = client.post(
        f"/boards/{board['id']}/items/connect",
        json={"item_a_id": item_a["id"], "item_b_id": item_b["id"]},
        headers=other_headers,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Authentication edge cases
# ---------------------------------------------------------------------------


def test_create_board_malformed_token_returns_401(client: TestClient) -> None:
    """A malformed Bearer token is rejected with 401."""
    r = client.post(
        "/boards",
        json=_BOARD_PAYLOAD,
        headers={"Authorization": "Bearer not.a.valid.token"},
    )
    assert r.status_code == 401


def test_create_board_token_with_non_uuid_sub_returns_401(client: TestClient) -> None:
    """A token whose 'sub' claim is not a valid UUID is rejected with 401."""
    token = jwt.encode(
        {"sub": "not-a-uuid", "exp": datetime.now(timezone.utc) + timedelta(days=7)},
        os.environ["JWT_SECRET"],
        algorithm=os.environ["JWT_ALGORITHM"],
    )
    r = client.post(
        "/boards",
        json=_BOARD_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


def test_health(client: TestClient) -> None:
    """The health endpoint reports the service as ok."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "boards"}
