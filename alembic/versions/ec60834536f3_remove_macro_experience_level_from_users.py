"""remove macro_experience_level from users

Revision ID: ec60834536f3
Revises: a8c083736a17
Create Date: 2026-01-23 23:32:46.463353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec60834536f3'
down_revision: Union[str, Sequence[str], None] = 'a8c083736a17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('users', 'macro_experience_level')


def downgrade() -> None:
    """Downgrade schema."""
    # Re-add the column. We assume the enum type 'experiencelevel' already exists in the DB.
    op.add_column('users', sa.Column('macro_experience_level', sa.Enum('beginner', 'intermediate', 'advanced', 'expert', name='experiencelevel'), nullable=True))
