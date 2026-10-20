"""add admin governance fields and action logs

Revision ID: c3f9a7b2d1e4
Revises: a9c31d7e2b44
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3f9a7b2d1e4"
down_revision: Union[str, None] = "a9c31d7e2b44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("status_reason", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("status_updated_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("categories") as batch_op:
        batch_op.add_column(
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0")
        )

    with op.batch_alter_table("listings") as batch_op:
        batch_op.add_column(sa.Column("status_reason", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("0"))
        )
        batch_op.add_column(sa.Column("featured_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("featured_by", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("featured_reason", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("moderated_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("moderated_by", sa.Integer(), nullable=True))
        batch_op.create_index("ix_listings_is_featured", ["is_featured"], unique=False)
        batch_op.create_foreign_key(
            "fk_listings_featured_by_users", "users", ["featured_by"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_listings_moderated_by_users", "users", ["moderated_by"], ["id"]
        )

    with op.batch_alter_table("reports") as batch_op:
        batch_op.add_column(sa.Column("handled_at", sa.DateTime(), nullable=True))

    op.create_table(
        "admin_action_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=30), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_action_logs_admin_id", "admin_action_logs", ["admin_id"], unique=False)
    op.create_index("ix_admin_action_logs_action", "admin_action_logs", ["action"], unique=False)
    op.create_index(
        "ix_admin_action_logs_target_type", "admin_action_logs", ["target_type"], unique=False
    )
    op.create_index(
        "ix_admin_action_logs_target_id", "admin_action_logs", ["target_id"], unique=False
    )
    op.create_index(
        "ix_admin_action_logs_created_at", "admin_action_logs", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_admin_action_logs_created_at", table_name="admin_action_logs")
    op.drop_index("ix_admin_action_logs_target_id", table_name="admin_action_logs")
    op.drop_index("ix_admin_action_logs_target_type", table_name="admin_action_logs")
    op.drop_index("ix_admin_action_logs_action", table_name="admin_action_logs")
    op.drop_index("ix_admin_action_logs_admin_id", table_name="admin_action_logs")
    op.drop_table("admin_action_logs")

    with op.batch_alter_table("reports") as batch_op:
        batch_op.drop_column("handled_at")

    with op.batch_alter_table("listings") as batch_op:
        batch_op.drop_constraint("fk_listings_moderated_by_users", type_="foreignkey")
        batch_op.drop_constraint("fk_listings_featured_by_users", type_="foreignkey")
        batch_op.drop_index("ix_listings_is_featured")
        batch_op.drop_column("moderated_by")
        batch_op.drop_column("moderated_at")
        batch_op.drop_column("featured_reason")
        batch_op.drop_column("featured_by")
        batch_op.drop_column("featured_at")
        batch_op.drop_column("is_featured")
        batch_op.drop_column("status_reason")

    with op.batch_alter_table("categories") as batch_op:
        batch_op.drop_column("sort_order")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("status_updated_at")
        batch_op.drop_column("status_reason")
