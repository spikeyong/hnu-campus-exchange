"""add email binding and explicit course demo states

Revision ID: a9c31d7e2b44
Revises: f7a81c2d4e90
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9c31d7e2b44"
down_revision: Union[str, None] = "f7a81c2d4e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("email_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("email_ciphertext", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("email_verified_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column("verification_method", sa.String(length=20), nullable=False, server_default="none")
        )
        batch_op.create_index("ix_users_email_hash", ["email_hash"], unique=True)

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE users SET verification_method = 'manual' "
            "WHERE role = 'student' AND verification_status = 'verified'"
        )
    )
    bind.execute(sa.text("UPDATE users SET verification_method = 'admin' WHERE role = 'admin'"))

    op.create_table(
        "email_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("email_hash", sa.String(length=64), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_codes_user_id", "email_codes", ["user_id"], unique=False)
    op.create_index("ix_email_codes_email_hash", "email_codes", ["email_hash"], unique=False)
    op.create_index("ix_email_codes_sent_at", "email_codes", ["sent_at"], unique=False)

    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(
            sa.Column("demo_payment_status", sa.String(length=20), nullable=False, server_default="unpaid")
        )
        batch_op.add_column(sa.Column("demo_paid_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_column("demo_paid_at")
        batch_op.drop_column("demo_payment_status")

    op.drop_index("ix_email_codes_sent_at", table_name="email_codes")
    op.drop_index("ix_email_codes_email_hash", table_name="email_codes")
    op.drop_index("ix_email_codes_user_id", table_name="email_codes")
    op.drop_table("email_codes")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_email_hash")
        batch_op.drop_column("verification_method")
        batch_op.drop_column("email_verified_at")
        batch_op.drop_column("email_ciphertext")
        batch_op.drop_column("email_hash")
