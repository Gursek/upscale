"""set midnight business rollover default

Revision ID: c90e9e20ee3d
Revises: b0685882aad9
Create Date: 2026-06-15 19:46:14.763203

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c90e9e20ee3d'
down_revision = 'b0685882aad9'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE users SET business_day_cutoff = '00:00' "
        "WHERE business_day_cutoff IS NULL OR business_day_cutoff = '23:59'"
    )


def downgrade():
    op.execute(
        "UPDATE users SET business_day_cutoff = '23:59' "
        "WHERE business_day_cutoff = '00:00'"
    )
