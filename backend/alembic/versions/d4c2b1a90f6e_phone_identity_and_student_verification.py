"""replace email identity with phone identity and manual student verification

Revision ID: d4c2b1a90f6e
Revises: 9b74f8d21f10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4c2b1a90f6e"
down_revision: Union[str, None] = "9b74f8d21f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("username", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("phone_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("phone_ciphertext", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("phone_last4", sa.String(length=4), nullable=True))
        batch_op.add_column(sa.Column("phone_verified_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("student_no_hash", sa.String(length=64), nullable=True))
        batch_op.create_index("ix_users_username", ["username"], unique=True)
        batch_op.create_index("ix_users_phone_hash", ["phone_hash"], unique=True)
        batch_op.create_index("ix_users_student_no_hash", ["student_no_hash"], unique=True)

    bind = op.get_bind()
    admin_ids = bind.execute(sa.text("SELECT id FROM users WHERE role = 'admin' ORDER BY id")).scalars().all()
    for position, admin_id in enumerate(admin_ids):
        username = "admin" if position == 0 else f"admin-{admin_id}"
        bind.execute(sa.text("UPDATE users SET username = :username WHERE id = :user_id"), {"username": username, "user_id": admin_id})

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_email")
        batch_op.drop_column("email")

    existing_tables = set(sa.inspect(bind).get_table_names())
    if "sms_codes" not in existing_tables:
        op.create_table(
            "sms_codes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("phone_hash", sa.String(length=64), nullable=False),
            sa.Column("code_hash", sa.String(length=64), nullable=False),
            sa.Column("purpose", sa.String(length=30), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("sent_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("consumed_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_sms_codes_phone_hash", "sms_codes", ["phone_hash"], unique=False)
        op.create_index("ix_sms_codes_sent_at", "sms_codes", ["sent_at"], unique=False)

    if "student_verifications" not in existing_tables:
        op.create_table(
            "student_verifications",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("challenge_code", sa.String(length=20), nullable=False),
            sa.Column("evidence_storage_key", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("review_note", sa.String(length=500), nullable=True),
            sa.Column("reviewer_id", sa.Integer(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_student_verifications_status", "student_verifications", ["status"], unique=False)
        op.create_index("ix_student_verifications_user_id", "student_verifications", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_student_verifications_user_id", table_name="student_verifications")
    op.drop_index("ix_student_verifications_status", table_name="student_verifications")
    op.drop_table("student_verifications")
    op.drop_index("ix_sms_codes_sent_at", table_name="sms_codes")
    op.drop_index("ix_sms_codes_phone_hash", table_name="sms_codes")
    op.drop_table("sms_codes")

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(length=255), nullable=True))
        batch_op.create_index("ix_users_email", ["email"], unique=True)
        batch_op.drop_index("ix_users_student_no_hash")
        batch_op.drop_index("ix_users_phone_hash")
        batch_op.drop_index("ix_users_username")
        batch_op.drop_column("student_no_hash")
        batch_op.drop_column("phone_verified_at")
        batch_op.drop_column("phone_last4")
        batch_op.drop_column("phone_ciphertext")
        batch_op.drop_column("phone_hash")
        batch_op.drop_column("username")
