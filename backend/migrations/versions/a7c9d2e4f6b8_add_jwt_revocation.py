"""add jwt revocation

Revision ID: a7c9d2e4f6b8
Revises: f5b7c2d8a4e6
Create Date: 2026-06-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a7c9d2e4f6b8"
down_revision = "f5b7c2d8a4e6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tokens_revoked_before", sa.DateTime(), nullable=True))

    op.create_table(
        "token_blocklist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("token_type", sa.String(length=10), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti"),
    )
    op.create_index(op.f("ix_token_blocklist_jti"), "token_blocklist", ["jti"], unique=False)
    op.create_index(op.f("ix_token_blocklist_user_id"), "token_blocklist", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_token_blocklist_user_id"), table_name="token_blocklist")
    op.drop_index(op.f("ix_token_blocklist_jti"), table_name="token_blocklist")
    op.drop_table("token_blocklist")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("tokens_revoked_before")
