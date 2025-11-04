"""add_conversation_messages_table

Revision ID: a39b4c5d2feb
Revises: 12f1cab0500b
Create Date: 2025-11-03 22:25:41.688187

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a39b4c5d2feb'
down_revision: Union[str, None] = '12f1cab0500b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
