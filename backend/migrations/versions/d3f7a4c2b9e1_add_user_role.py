"""add user role

Revision ID: d3f7a4c2b9e1
Revises: b20f4d7f3b9a
Create Date: 2026-06-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d3f7a4c2b9e1"
down_revision = "b20f4d7f3b9a"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "role",
                sa.String(length=20),
                nullable=False,
                server_default="owner",
            )
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("role")
