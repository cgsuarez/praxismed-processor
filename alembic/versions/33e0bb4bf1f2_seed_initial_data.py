"""seed_initial_data

Revision ID: 33e0bb4bf1f2
Revises: 1e1417619f91
Create Date: 2026-01-04 22:55:00.985137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision: str = '33e0bb4bf1f2'
down_revision: Union[str, Sequence[str], None] = '1e1417619f91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
