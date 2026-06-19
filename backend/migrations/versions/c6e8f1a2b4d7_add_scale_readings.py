"""add persisted Raspberry Pi scale readings

Revision ID: c6e8f1a2b4d7
Revises: a7c9d2e4f6b8
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa


revision = "c6e8f1a2b4d7"
down_revision = "a7c9d2e4f6b8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scale_readings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=100), nullable=False),
        sa.Column("weight_kg", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scale_readings_user_id", "scale_readings", ["user_id"])
    op.create_index("ix_scale_readings_captured_at", "scale_readings", ["captured_at"])


def downgrade():
    op.drop_index("ix_scale_readings_captured_at", table_name="scale_readings")
    op.drop_index("ix_scale_readings_user_id", table_name="scale_readings")
    op.drop_table("scale_readings")
