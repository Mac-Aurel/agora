import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ValidationStatus(str, enum.Enum):
    """Shared status for board items and contributions awaiting moderation."""

    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"


class ContributionType(str, enum.Enum):
    """Type of a contribution submitted on a board item."""

    ANNOTATION = "annotation"
    LINK = "link"
    COMMENT = "comment"


class Board(Base):
    """SQLAlchemy model for the boards table."""

    __tablename__ = "boards"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Référence users(id) (table créée par le service auth dans la même base
    # PostgreSQL partagée). Pas de modèle User importé ici pour ne pas coupler
    # les services : seule la contrainte FK au niveau base de données est posée.
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text).with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        onupdate=func.now(),
    )


class BoardItem(Base):
    """SQLAlchemy model for the board_items table."""

    __tablename__ = "board_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    board_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # TODO: ajouter ForeignKey("contents.id") une fois le service `content`
    # implémenté et la table `contents` créée dans la base partagée.
    content_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        nullable=False,
        index=True,
    )
    added_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    status: Mapped[ValidationStatus] = mapped_column(
        SAEnum(ValidationStatus, name="validation_status"),
        nullable=False,
        default=ValidationStatus.VALIDATED,
        server_default=ValidationStatus.VALIDATED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )


class Contribution(Base):
    """SQLAlchemy model for the contributions table."""

    __tablename__ = "contributions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    board_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("board_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contributor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    type: Mapped[ContributionType] = mapped_column(
        SAEnum(ContributionType, name="contribution_type"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ValidationStatus] = mapped_column(
        SAEnum(ValidationStatus, name="validation_status"),
        nullable=False,
        default=ValidationStatus.PENDING,
        server_default=ValidationStatus.PENDING.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )


class ItemConnection(Base):
    """SQLAlchemy model for the item_connections table."""

    __tablename__ = "item_connections"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    item_a_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("board_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_b_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("board_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
