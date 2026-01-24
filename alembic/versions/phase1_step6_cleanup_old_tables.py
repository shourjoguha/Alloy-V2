"""Drop old_ tables after successful schema refactor.

This migration cleans up the temporary tables created during the
SessionSection -> ExerciseRole consolidation refactor.

Steps:
1. Drop old_movements table (backup of original movements table)
2. Drop old_session_exercises table (backup of original session_exercises table)

These tables were used during the safe migration process and are no
longer needed after the successful table swap in Step 4 and FK fix in Step 5.

Revision ID: phase1_step6_cleanup
Revises: phase1_step5_fix_fk
Create Date: 2026-01-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'phase1_step6_cleanup'
down_revision = 'phase1_step5_fix_fk'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop old_ tables after successful refactor."""
    
    # Drop old backup tables
    op.drop_table('old_session_exercises')
    op.drop_table('old_movements')


def downgrade() -> None:
    """Restore old_ tables if needed for rollback."""
    
    # Restore old backup tables
    op.create_table(
        'old_session_exercises',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.Integer(), nullable=False, index=True),
        sa.Column('movement_id', sa.Integer(), nullable=False, index=True),
        sa.Column('role', sa.Enum('warmup', 'main', 'accessory', 'skill', 'finisher', 'cooldown', 'cardio', 'conditioning', name='exerciserole'), nullable=True),
        sa.Column('session_section', sa.Enum('warmup', 'main', 'accessory', 'skill', 'finisher', 'cooldown', 'cardio', 'conditioning', name='sessionsection'), nullable=True, index=True),
        sa.Column('circuit_id', sa.Integer(), nullable=True, index=True),
        sa.Column('order_in_session', sa.Integer(), nullable=False),
        sa.Column('superset_group', sa.Integer(), nullable=True),
        sa.Column('target_sets', sa.Integer(), nullable=True),
        sa.Column('target_rep_range_min', sa.Integer(), nullable=True),
        sa.Column('target_rep_range_max', sa.Integer(), nullable=True),
        sa.Column('target_rpe', sa.Float(), nullable=True),
        sa.Column('target_rir', sa.Float(), nullable=True),
        sa.Column('target_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('default_rest_seconds', sa.Integer(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['circuit_id'], ['circuit_templates.id'], ),
        sa.ForeignKeyConstraint(['movement_id'], ['movements.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_old_session_exercises_session_section', 'old_session_exercises', ['session_section'], unique=False)
    
    op.create_table(
        'old_movements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=True),
        sa.Column('primary_pattern', sa.Enum('squat', 'hinge', 'horizontal_push', 'vertical_push', 'horizontal_pull', 'vertical_pull', 'carry', 'core', 'lunge', 'rotation', 'plyometric', 'olympic', 'isolation', 'mobility', 'isometric', 'conditioning', 'cardio', name='movementpattern'), nullable=True),
        sa.Column('primary_region', sa.Enum('anterior lower', 'posterior lower', 'shoulder', 'anterior upper', 'posterior upper', 'full body', 'lower body', 'upper body', 'core', name='primaryregion'), nullable=True),
        sa.Column('primary_muscle', sa.String(), nullable=True),
        sa.Column('primary_discipline', sa.String(), nullable=True),
        sa.Column('skill_level', sa.Enum('beginner', 'intermediate', 'advanced', 'expert', 'elite', name='skilllevel'), nullable=True),
        sa.Column('cns_load', sa.Enum('very_low', 'low', 'moderate', 'high', 'very_high', name='cnsload'), nullable=True),
        sa.Column('metric_type', sa.Enum('reps', 'time', 'time_under_tension', 'distance', name='metrictype'), nullable=True),
        sa.Column('block_type', sa.String(), nullable=True),
        sa.Column('substitution_group', sa.String(), nullable=True, index=True),
        sa.Column('tags', sa.String(), nullable=True),
        sa.Column('discipline_tags', sa.String(), nullable=True),
        sa.Column('instructions', sa.String(), nullable=True),
        sa.Column('equipment', sa.String(), nullable=True),
        sa.Column('video_url', sa.String(), nullable=True),
        sa.Column('is_compound', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True, index=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_old_movements_primary_pattern', 'old_movements', ['primary_pattern'], unique=False)
    op.create_index('ix_old_movements_substitution_group', 'old_movements', ['substitution_group'], unique=False)
