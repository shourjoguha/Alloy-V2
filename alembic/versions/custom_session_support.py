"""Add custom session support

Revision ID: custom_session_support
Revises: extend_microcycle_length_to_14
Create Date: 2026-01-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'custom_session_support'
down_revision: Union[str, Sequence[str], None] = 'extend_microcycle_length_to_14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Session modifications
    op.add_column('sessions', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'sessions', 'users', ['user_id'], ['id'])
    op.alter_column('sessions', 'microcycle_id', existing_type=sa.Integer(), nullable=True)
    op.add_column('sessions', sa.Column('total_stimulus', sa.Float(), nullable=True))
    op.add_column('sessions', sa.Column('total_fatigue', sa.Float(), nullable=True))
    op.add_column('sessions', sa.Column('cns_fatigue', sa.Float(), nullable=True))
    op.add_column('sessions', sa.Column('muscle_volume_json', sa.JSON(), nullable=True))
    
    # SessionExercise modifications
    op.add_column('session_exercises', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'session_exercises', 'users', ['user_id'], ['id'])
    op.add_column('session_exercises', sa.Column('stimulus', sa.Float(), nullable=True))
    op.add_column('session_exercises', sa.Column('fatigue', sa.Float(), nullable=True))


def downgrade() -> None:
    # Revert SessionExercise
    op.drop_column('session_exercises', 'fatigue')
    op.drop_column('session_exercises', 'stimulus')
    op.drop_constraint(None, 'session_exercises', type_='foreignkey')
    op.drop_column('session_exercises', 'user_id')
    
    # Revert Session
    op.drop_column('sessions', 'muscle_volume_json')
    op.drop_column('sessions', 'cns_fatigue')
    op.drop_column('sessions', 'total_fatigue')
    op.drop_column('sessions', 'total_stimulus')
    op.alter_column('sessions', 'microcycle_id', existing_type=sa.Integer(), nullable=False)
    op.drop_constraint(None, 'sessions', type_='foreignkey')
    op.drop_column('sessions', 'user_id')
