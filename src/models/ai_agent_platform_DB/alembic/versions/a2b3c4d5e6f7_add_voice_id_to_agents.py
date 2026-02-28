"""add voice_id to agents

Revision ID: a2b3c4d5e6f7
Revises: 1a4d75910fee
Create Date: 2026-02-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = '1a4d75910fee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('agents', sa.Column('voice_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('agents', 'voice_id')
