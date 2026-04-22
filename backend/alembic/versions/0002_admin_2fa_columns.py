"""add admin two factor fields

Revision ID: 0002_admin_2fa_columns
Revises: 0001_initial_platform
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_admin_2fa_columns"
down_revision = "0001_initial_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("two_factor_secret", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("two_factor_recovery_codes", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "two_factor_recovery_codes")
    op.drop_column("users", "two_factor_secret")
