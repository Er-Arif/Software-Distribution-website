"""initial platform schema

Revision ID: 0001_initial_platform
Revises:
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_platform"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    # The initial migration is intentionally generated from SQLAlchemy metadata in early
    # development. Run `alembic revision --autogenerate` before production freeze.


def downgrade() -> None:
    pass
