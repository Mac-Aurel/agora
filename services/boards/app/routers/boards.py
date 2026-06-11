import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user_id, get_db, get_optional_user_id
from app.models.board import (
    Board,
    BoardItem,
    Contribution,
    ItemConnection,
    ValidationStatus,
)
from app.schemas.board import (
    BoardCreate,
    BoardDetailResponse,
    BoardItemCreate,
    BoardItemResponse,
    BoardResponse,
    BoardUpdate,
    ContributionCreate,
    ContributionResponse,
    ItemConnectionCreate,
    ItemConnectionResponse,
)
from app.services import boards_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_board_or_404(db: Session, board_id: uuid.UUID) -> Board:
    """Fetch a board or raise 404 if it does not exist."""
    board = boards_service.get_board(db, board_id)
    if board is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Board not found"
        )
    return board


def _get_item_or_404(db: Session, board_id: uuid.UUID, item_id: uuid.UUID) -> BoardItem:
    """Fetch a board item belonging to the given board or raise 404."""
    item = boards_service.get_board_item(db, board_id, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )
    return item


def _get_contribution_or_404(db: Session, contribution_id: uuid.UUID) -> Contribution:
    """Fetch a contribution or raise 404 if it does not exist."""
    contribution = boards_service.get_contribution(db, contribution_id)
    if contribution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found"
        )
    return contribution


def _ensure_visible(board: Board, user_id: Optional[uuid.UUID]) -> None:
    """Raise 404 if the board is private and the user is not its owner.

    Private boards are hidden as if they did not exist, to avoid leaking
    their existence to unauthorized users.
    """
    if not board.is_public and board.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Board not found"
        )


def _ensure_owner(board: Board, user_id: uuid.UUID) -> None:
    """Raise 403 if the user is not the board's owner."""
    if board.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the board owner can perform this action",
        )


# ---------------------------------------------------------------------------
# Boards
# ---------------------------------------------------------------------------


@router.get(
    "/boards",
    response_model=list[BoardResponse],
    summary="List public boards",
)
def list_boards(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Board]:
    """List public boards, most recent first.

    Args:
        skip: Pagination offset.
        limit: Maximum number of boards to return (1-100).
        db: Database session (injected).

    Returns:
        A list of public boards.
    """
    return list(boards_service.list_public_boards(db, skip=skip, limit=limit))


@router.post(
    "/boards",
    response_model=BoardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a board",
)
def create_board(
    data: BoardCreate,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Board:
    """Create a new board owned by the authenticated user.

    Args:
        data: Board creation payload.
        db: Database session (injected).
        user_id: UUID of the authenticated user (injected).

    Returns:
        The newly created board.
    """
    return boards_service.create_board(db, user_id, data)


@router.get(
    "/boards/{board_id}",
    response_model=BoardDetailResponse,
    summary="Get board details",
)
def get_board(
    board_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: Optional[uuid.UUID] = Depends(get_optional_user_id),
) -> BoardDetailResponse:
    """Return a board's details along with its items.

    Args:
        board_id: UUID of the board.
        db: Database session (injected).
        user_id: UUID of the authenticated user, if any (injected).

    Returns:
        The board details, including its items.

    Raises:
        HTTPException: 404 if the board does not exist, or is private and the
            requester is not its owner.
    """
    board = _get_board_or_404(db, board_id)
    _ensure_visible(board, user_id)
    items = boards_service.list_items(db, board_id)
    return BoardDetailResponse(
        **BoardResponse.model_validate(board).model_dump(),
        items=[BoardItemResponse.model_validate(item) for item in items],
    )


@router.put(
    "/boards/{board_id}",
    response_model=BoardResponse,
    summary="Update a board",
)
def update_board(
    board_id: uuid.UUID,
    data: BoardUpdate,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Board:
    """Update a board's metadata.

    Args:
        board_id: UUID of the board to update.
        data: Fields to update.
        db: Database session (injected).
        user_id: UUID of the authenticated user (injected).

    Returns:
        The updated board.

    Raises:
        HTTPException: 404 if the board does not exist, 403 if the requester
            is not the board's owner.
    """
    board = _get_board_or_404(db, board_id)
    _ensure_owner(board, user_id)
    return boards_service.update_board(db, board, data)


@router.delete(
    "/boards/{board_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a board",
)
def delete_board(
    board_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Delete a board and all its items, contributions and connections.

    Args:
        board_id: UUID of the board to delete.
        db: Database session (injected).
        user_id: UUID of the authenticated user (injected).

    Raises:
        HTTPException: 404 if the board does not exist, 403 if the requester
            is not the board's owner.
    """
    board = _get_board_or_404(db, board_id)
    _ensure_owner(board, user_id)
    boards_service.delete_board(db, board)


# ---------------------------------------------------------------------------
# Board items
# ---------------------------------------------------------------------------


@router.post(
    "/boards/{board_id}/items",
    response_model=BoardItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to a board",
)
def add_item(
    board_id: uuid.UUID,
    data: BoardItemCreate,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> BoardItem:
    """Add a content item to a board.

    Only the board owner can curate the board's items directly. Other users
    contribute via `POST /boards/{board_id}/items/{item_id}/contribute`.

    Args:
        board_id: UUID of the board.
        data: Item creation payload.
        db: Database session (injected).
        user_id: UUID of the authenticated user (injected).

    Returns:
        The newly created board item (status=validated).

    Raises:
        HTTPException: 404 if the board does not exist, 403 if the requester
            is not the board's owner.
    """
    board = _get_board_or_404(db, board_id)
    _ensure_owner(board, user_id)
    return boards_service.add_item(db, board_id, user_id, data)


@router.delete(
    "/boards/{board_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an item from a board",
)
def remove_item(
    board_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Remove an item from a board.

    Args:
        board_id: UUID of the board.
        item_id: UUID of the item to remove.
        db: Database session (injected).
        user_id: UUID of the authenticated user (injected).

    Raises:
        HTTPException: 404 if the board or item does not exist, 403 if the
            requester is not the board's owner.
    """
    board = _get_board_or_404(db, board_id)
    _ensure_owner(board, user_id)
    item = _get_item_or_404(db, board_id, item_id)
    boards_service.remove_item(db, item)


@router.post(
    "/boards/{board_id}/items/connect",
    response_model=ItemConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect two items of a board",
)
def connect_items(
    board_id: uuid.UUID,
    data: ItemConnectionCreate,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ItemConnection:
    """Create a labeled connection between two items of the same board.

    Args:
        board_id: UUID of the board the items belong to.
        data: Connection creation payload.
        db: Database session (injected).
        user_id: UUID of the authenticated user (injected).

    Returns:
        The newly created connection.

    Raises:
        HTTPException: 404 if the board does not exist (or is private and
            invisible to the requester), or if either item does not belong
            to the board.
    """
    board = _get_board_or_404(db, board_id)
    _ensure_visible(board, user_id)
    if not boards_service.items_belong_to_board(
        db, board_id, [data.item_a_id, data.item_b_id]
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both items not found on this board",
        )
    return boards_service.create_connection(db, user_id, data)


# ---------------------------------------------------------------------------
# Contributions
# ---------------------------------------------------------------------------


@router.post(
    "/boards/{board_id}/items/{item_id}/contribute",
    response_model=ContributionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a contribution on a board item",
)
def contribute(
    board_id: uuid.UUID,
    item_id: uuid.UUID,
    data: ContributionCreate,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Contribution:
    """Submit an annotation, link or comment on a board item, pending validation.

    Args:
        board_id: UUID of the board.
        item_id: UUID of the item being contributed to.
        data: Contribution creation payload.
        db: Database session (injected).
        user_id: UUID of the authenticated user (injected).

    Returns:
        The newly created contribution (status=pending).

    Raises:
        HTTPException: 404 if the board (or is private and invisible to the
            requester) or item does not exist.
    """
    board = _get_board_or_404(db, board_id)
    _ensure_visible(board, user_id)
    item = _get_item_or_404(db, board_id, item_id)
    return boards_service.create_contribution(db, item.id, user_id, data)


@router.get(
    "/boards/{board_id}/contributions",
    response_model=list[ContributionResponse],
    summary="List pending contributions for a board",
)
def list_contributions(
    board_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[Contribution]:
    """List pending contributions across all items of a board.

    Args:
        board_id: UUID of the board.
        db: Database session (injected).
        user_id: UUID of the authenticated user (injected).

    Returns:
        A list of pending contributions.

    Raises:
        HTTPException: 404 if the board does not exist, 403 if the requester
            is not the board's owner.
    """
    board = _get_board_or_404(db, board_id)
    _ensure_owner(board, user_id)
    return list(boards_service.list_pending_contributions(db, board_id))


@router.put(
    "/contributions/{contribution_id}/validate",
    response_model=ContributionResponse,
    summary="Validate a pending contribution",
)
def validate_contribution(
    contribution_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Contribution:
    """Validate a pending contribution.

    Args:
        contribution_id: UUID of the contribution to validate.
        db: Database session (injected).
        user_id: UUID of the authenticated user (injected).

    Returns:
        The contribution with status=validated.

    Raises:
        HTTPException: 404 if the contribution does not exist, 403 if the
            requester is not the owner of the board it belongs to, 409 if the
            contribution has already been processed.
    """
    contribution = _get_contribution_or_404(db, contribution_id)
    board = boards_service.get_board_for_contribution(db, contribution)
    if board is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found"
        )
    _ensure_owner(board, user_id)
    if contribution.status != ValidationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contribution has already been processed",
        )
    return boards_service.set_contribution_status(
        db, contribution, ValidationStatus.VALIDATED
    )


@router.put(
    "/contributions/{contribution_id}/reject",
    response_model=ContributionResponse,
    summary="Reject a pending contribution",
)
def reject_contribution(
    contribution_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Contribution:
    """Reject a pending contribution.

    Args:
        contribution_id: UUID of the contribution to reject.
        db: Database session (injected).
        user_id: UUID of the authenticated user (injected).

    Returns:
        The contribution with status=rejected.

    Raises:
        HTTPException: 404 if the contribution does not exist, 403 if the
            requester is not the owner of the board it belongs to, 409 if the
            contribution has already been processed.
    """
    contribution = _get_contribution_or_404(db, contribution_id)
    board = boards_service.get_board_for_contribution(db, contribution)
    if board is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found"
        )
    _ensure_owner(board, user_id)
    if contribution.status != ValidationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contribution has already been processed",
        )
    return boards_service.set_contribution_status(
        db, contribution, ValidationStatus.REJECTED
    )
