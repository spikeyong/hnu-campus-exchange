"""expand encrypted student number storage

Revision ID: f7a81c2d4e90
Revises: d4c2b1a90f6e
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a81c2d4e90"
down_revision: Union[str, None] = "d4c2b1a90f6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "student_no",
            existing_type=sa.String(length=80),
            type_=sa.String(length=512),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "student_no",
            existing_type=sa.String(length=512),
            type_=sa.String(length=80),
            existing_nullable=True,
        )
