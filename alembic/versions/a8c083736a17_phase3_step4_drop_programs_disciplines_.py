"""phase3_step4_drop_programs_disciplines_json_column

Revision ID: a8c083736a17
Revises: c317c87fdf7b
Create Date: 2026-01-23 18:33:04.988217

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8c083736a17'
down_revision: Union[str, Sequence[str], None] = 'c317c87fdf7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('programs', 'disciplines_json')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('programs', sa.Column('disciplines_json', sa.JSON(), nullable=True))
