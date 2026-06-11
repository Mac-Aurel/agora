import uuid
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.models.board import (
    Board,
    BoardItem,
    Contribution,
    ItemConnection,
    ValidationStatus,
)
from app.schemas.board import (
    BoardCreate,
    BoardItemCreate,
    BoardUpdate,
    ContributionCreate,
    ItemConnectionCreate,
)

# ---------------------------------------------------------------------------
# Boards
# ---------------------------------------------------------------------------


def create_board(db: Session, owner_id: uuid.UUID, data: BoardCreate) -> Board:
    """Create a new board owned by the given user.

    Args:
        db: Active SQLAlchemy session.
        owner_id: UUID of the authenticated user creating the board.
        data: Validated board creation payload.

    Returns:
        The newly created and refreshed Board instance.
    """
    board = Board(
        id=uuid.uuid4(),
        owner_id=owner_id,
        title=data.title,
        description=data.description,
        tags=data.tags,
        is_public=data.is_public,
    )
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


def get_board(db: Session, board_id: uuid.UUID) -> Optional[Board]:
    """Fetch a board by its id.

    Args:
        db: Active SQLAlchemy session.
        board_id: UUID of the board to fetch.

    Returns:
        The Board instance if found, None otherwise.
    """
    return db.get(Board, board_id)


def list_public_boards(db: Session, skip: int = 0, limit: int = 50) -> Sequence[Board]:
    """List public boards, most recent first.

    Args:
        db: Active SQLAlchemy session.
        skip: Number of boards to skip (pagination offset).
        limit: Maximum number of boards to return.

    Returns:
        A sequence of public Board instances.
    """
    return (
        db.query(Board)
        .filter(Board.is_public.is_(True))
        .order_by(Board.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_board(db: Session, board: Board, data: BoardUpdate) -> Board:
    """Apply a partial update to a board.

    Args:
        db: Active SQLAlchemy session.
        board: The Board instance to update.
        data: Fields to update (only set fields are applied).

    Returns:
        The updated and refreshed Board instance.
    """
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(board, field, value)
    db.commit()
    db.refresh(board)
    return board


def delete_board(db: Session, board: Board) -> None:
    """Delete a board and cascade-delete its items, contributions and connections.

    Args:
        db: Active SQLAlchemy session.
        board: The Board instance to delete.
    """
    db.delete(board)
    db.commit()


# ---------------------------------------------------------------------------
# Board items
# ---------------------------------------------------------------------------


def add_item(
    db: Session,
    board_id: uuid.UUID,
    added_by: uuid.UUID,
    data: BoardItemCreate,
) -> BoardItem:
    """Add an item to a board.

    Args:
        db: Active SQLAlchemy session.
        board_id: UUID of the board receiving the item.
        added_by: UUID of the user adding the item.
        data: Validated item creation payload.

    Returns:
        The newly created and refreshed BoardItem instance.
    """
    item = BoardItem(
        id=uuid.uuid4(),
        board_id=board_id,
        content_id=data.content_id,
        added_by=added_by,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_items(db: Session, board_id: uuid.UUID) -> Sequence[BoardItem]:
    """List the items of a board, oldest first.

    Args:
        db: Active SQLAlchemy session.
        board_id: UUID of the board.

    Returns:
        A sequence of BoardItem instances belonging to the board.
    """
    return (
        db.query(BoardItem)
        .filter(BoardItem.board_id == board_id)
        .order_by(BoardItem.created_at)
        .all()
    )


def get_board_item(
    db: Session, board_id: uuid.UUID, item_id: uuid.UUID
) -> Optional[BoardItem]:
    """Fetch an item belonging to a specific board.

    Args:
        db: Active SQLAlchemy session.
        board_id: UUID of the board the item must belong to.
        item_id: UUID of the item to fetch.

    Returns:
        The BoardItem instance if found and belonging to the board, None otherwise.
    """
    return (
        db.query(BoardItem)
        .filter(BoardItem.id == item_id, BoardItem.board_id == board_id)
        .first()
    )


def remove_item(db: Session, item: BoardItem) -> None:
    """Delete a board item and cascade-delete its contributions and connections.

    Args:
        db: Active SQLAlchemy session.
        item: The BoardItem instance to delete.
    """
    db.delete(item)
    db.commit()


def items_belong_to_board(
    db: Session, board_id: uuid.UUID, item_ids: Sequence[uuid.UUID]
) -> bool:
    """Check that every given item id exists and belongs to the given board.

    Args:
        db: Active SQLAlchemy session.
        board_id: UUID of the board the items must belong to.
        item_ids: UUIDs of the items to check.

    Returns:
        True if all item ids belong to the board, False otherwise.
    """
    count = (
        db.query(BoardItem)
        .filter(BoardItem.board_id == board_id, BoardItem.id.in_(item_ids))
        .count()
    )
    return count == len(set(item_ids))


# ---------------------------------------------------------------------------
# Contributions
# ---------------------------------------------------------------------------


def create_contribution(
    db: Session,
    board_item_id: uuid.UUID,
    contributor_id: uuid.UUID,
    data: ContributionCreate,
) -> Contribution:
    """Submit a contribution on a board item, pending validation by the board owner.

    Args:
        db: Active SQLAlchemy session.
        board_item_id: UUID of the board item being contributed to.
        contributor_id: UUID of the user submitting the contribution.
        data: Validated contribution creation payload.

    Returns:
        The newly created and refreshed Contribution instance (status=pending).
    """
    contribution = Contribution(
        id=uuid.uuid4(),
        board_item_id=board_item_id,
        contributor_id=contributor_id,
        type=data.type,
        body=data.body,
    )
    db.add(contribution)
    db.commit()
    db.refresh(contribution)
    return contribution


def get_contribution(db: Session, contribution_id: uuid.UUID) -> Optional[Contribution]:
    """Fetch a contribution by its id.

    Args:
        db: Active SQLAlchemy session.
        contribution_id: UUID of the contribution to fetch.

    Returns:
        The Contribution instance if found, None otherwise.
    """
    return db.get(Contribution, contribution_id)


def list_pending_contributions(
    db: Session, board_id: uuid.UUID
) -> Sequence[Contribution]:
    """List pending contributions for all items of a board, oldest first.

    Args:
        db: Active SQLAlchemy session.
        board_id: UUID of the board.

    Returns:
        A sequence of pending Contribution instances.
    """
    return (
        db.query(Contribution)
        .join(BoardItem, Contribution.board_item_id == BoardItem.id)
        .filter(
            BoardItem.board_id == board_id,
            Contribution.status == ValidationStatus.PENDING,
        )
        .order_by(Contribution.created_at)
        .all()
    )


def get_board_for_contribution(
    db: Session, contribution: Contribution
) -> Optional[Board]:
    """Resolve the board a contribution belongs to, via its board item.

    Args:
        db: Active SQLAlchemy session.
        contribution: The Contribution instance.

    Returns:
        The Board instance the contribution's item belongs to, or None if the
        item or board no longer exists.
    """
    item = db.get(BoardItem, contribution.board_item_id)
    if item is None:
        return None
    return db.get(Board, item.board_id)


def set_contribution_status(
    db: Session, contribution: Contribution, status_value: ValidationStatus
) -> Contribution:
    """Update the status of a contribution.

    Args:
        db: Active SQLAlchemy session.
        contribution: The Contribution instance to update.
        status_value: The new status (validated or rejected).

    Returns:
        The updated and refreshed Contribution instance.
    """
    contribution.status = status_value
    db.commit()
    db.refresh(contribution)
    return contribution


# ---------------------------------------------------------------------------
# Item connections
# ---------------------------------------------------------------------------


def create_connection(
    db: Session, created_by: uuid.UUID, data: ItemConnectionCreate
) -> ItemConnection:
    """Create a connection between two items of the same board.

    Args:
        db: Active SQLAlchemy session.
        created_by: UUID of the user creating the connection.
        data: Validated connection creation payload.

    Returns:
        The newly created and refreshed ItemConnection instance.
    """
    connection = ItemConnection(
        id=uuid.uuid4(),
        item_a_id=data.item_a_id,
        item_b_id=data.item_b_id,
        label=data.label,
        created_by=created_by,
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection
