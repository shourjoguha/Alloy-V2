"""phase1_pre_refactor_snapshot

Revision ID: 970301065e1d
Revises: feab32325bef
Create Date: 2026-01-23 15:34:24.736111

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '970301065e1d'
down_revision: Union[str, Sequence[str], None] = 'feab32325bef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    
    Pre-Refactor Snapshot for Phase 1: Workout Content Optimization.
    This migration marks the current state before refactoring movements, session_exercises,
    muscles, and tags tables. Can be used as rollback point if needed.
    """
    pass


def downgrade() -> None:
    """Downgrade schema.
    
    Rollback to state before Phase 1 refactoring.
    """
    pass
