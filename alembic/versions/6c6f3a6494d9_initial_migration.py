"""initial migration

Revision ID: 6c6f3a6494d9
Revises: 
Create Date: 2026-06-26 17:02:37.920449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6c6f3a6494d9"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "executionmemory",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("instruction", sa.String(), nullable=False),
        sa.Column("instruction_key", sa.String(), nullable=False),
        sa.Column("decomposition", sa.String(), nullable=False),
        sa.Column("steps_json", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("api_call_count", sa.Integer(), nullable=False),
        sa.Column("failure_reason", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_executionmemory_instruction_key"), "executionmemory", ["instruction_key"], unique=False)

    op.create_table(
        "capabilitymemory",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("api_spec_json", sa.String(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("constraints_json", sa.String(), nullable=False),
        sa.Column("synthesized", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_capabilitymemory_name"), "capabilitymemory", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_capabilitymemory_name"), table_name="capabilitymemory")
    op.drop_table("capabilitymemory")
    op.drop_index(op.f("ix_executionmemory_instruction_key"), table_name="executionmemory")
    op.drop_table("executionmemory")
