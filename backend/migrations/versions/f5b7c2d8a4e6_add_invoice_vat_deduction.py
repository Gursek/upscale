"""add invoice vat deduction

Revision ID: f5b7c2d8a4e6
Revises: e4a8c1d9f2b3
Create Date: 2026-06-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f5b7c2d8a4e6"
down_revision = "e4a8c1d9f2b3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("invoices", schema=None) as batch_op:
        batch_op.add_column(sa.Column("vat_deduction", sa.Numeric(10, 2), nullable=True))


def downgrade():
    with op.batch_alter_table("invoices", schema=None) as batch_op:
        batch_op.drop_column("vat_deduction")
