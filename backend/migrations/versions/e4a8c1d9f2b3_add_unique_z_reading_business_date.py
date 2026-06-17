"""add unique z reading business date

Revision ID: e4a8c1d9f2b3
Revises: d3f7a4c2b9e1
Create Date: 2026-06-17 00:00:00.000000
"""

from alembic import op


revision = "e4a8c1d9f2b3"
down_revision = "d3f7a4c2b9e1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("z_readings", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_z_reading_user_business_date",
            ["user_id", "business_date"],
        )


def downgrade():
    with op.batch_alter_table("z_readings", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_z_reading_user_business_date",
            type_="unique",
        )
