"""add password reset otp

Revision ID: b20f4d7f3b9a
Revises: 08f6ea886096
Create Date: 2026-06-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b20f4d7f3b9a"
down_revision = "08f6ea886096"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("password_reset_otp_hash", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("password_reset_expires_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("password_reset_expires_at")
        batch_op.drop_column("password_reset_otp_hash")
