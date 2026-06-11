"""create boards tables

Revision ID: 0001
Revises:
Create Date: 2026-06-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_validation_status = postgresql.ENUM(
    "pending", "validated", "rejected", name="validation_status"
)
_contribution_type = postgresql.ENUM(
    "annotation", "link", "comment", name="contribution_type"
)


def upgrade() -> None:
    """Create the boards, board_items, contributions and item_connections tables.

    Note: board_items.content_id intentionally has no foreign key constraint
    yet, as the `contents` table does not exist (the `content` service is not
    implemented). The constraint should be added via a future migration once
    that table is created.
    """
    bind = op.get_bind()
    _validation_status.create(bind, checkfirst=True)
    _contribution_type.create(bind, checkfirst=True)

    op.create_table(
        "boards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column(
            "is_public", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_boards"),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_boards_owner_id_users"
        ),
    )
    op.create_index("ix_boards_owner_id", "boards", ["owner_id"])

    op.create_table(
        "board_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("board_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("added_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            _validation_status,
            nullable=False,
            server_default="validated",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_board_items"),
        sa.ForeignKeyConstraint(
            ["board_id"],
            ["boards.id"],
            name="fk_board_items_board_id_boards",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["added_by"], ["users.id"], name="fk_board_items_added_by_users"
        ),
    )
    op.create_index("ix_board_items_board_id", "board_items", ["board_id"])
    op.create_index("ix_board_items_content_id", "board_items", ["content_id"])

    op.create_table(
        "contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("board_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contributor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", _contribution_type, nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status",
            _validation_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_contributions"),
        sa.ForeignKeyConstraint(
            ["board_item_id"],
            ["board_items.id"],
            name="fk_contributions_board_item_id_board_items",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["contributor_id"],
            ["users.id"],
            name="fk_contributions_contributor_id_users",
        ),
    )
    op.create_index(
        "ix_contributions_board_item_id", "contributions", ["board_item_id"]
    )

    op.create_table(
        "item_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_a_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_b_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_item_connections"),
        sa.ForeignKeyConstraint(
            ["item_a_id"],
            ["board_items.id"],
            name="fk_item_connections_item_a_id_board_items",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["item_b_id"],
            ["board_items.id"],
            name="fk_item_connections_item_b_id_board_items",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_item_connections_created_by_users",
        ),
    )


def downgrade() -> None:
    """Drop the boards tables and their enum types."""
    op.drop_table("item_connections")
    op.drop_table("contributions")
    op.drop_index("ix_board_items_content_id", table_name="board_items")
    op.drop_index("ix_board_items_board_id", table_name="board_items")
    op.drop_table("board_items")
    op.drop_index("ix_boards_owner_id", table_name="boards")
    op.drop_table("boards")

    bind = op.get_bind()
    _contribution_type.drop(bind, checkfirst=True)
    _validation_status.drop(bind, checkfirst=True)
