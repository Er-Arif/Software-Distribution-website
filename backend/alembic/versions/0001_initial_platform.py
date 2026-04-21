"""initial platform schema

Revision ID: 0001_initial_platform
Revises:
Create Date: 2026-04-22
"""

from alembic import op
from app.db.base import Base
from app.db import models  # noqa: F401

revision = "0001_initial_platform"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
