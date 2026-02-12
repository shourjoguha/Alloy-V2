"""replace_elite_with_expert_in_skill_level_enum

Revision ID: a1b2c3d4e5f6
Revises: 01441a3eb2a8
Create Date: 2026-02-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '01441a3eb2a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Update all movements and user_skills with skill_level = 'elite' to 'expert'
    and remove 'elite' from the skill_level enum.
    """

    # Step 1: Update all movements with skill_level = 'elite' to 'expert'
    op.execute("""
        UPDATE movements
        SET skill_level = 'expert'
        WHERE skill_level = 'elite'
    """)

    # Update all user_skills with skill_level = 'elite' to 'expert'
    op.execute("""
        UPDATE user_skills
        SET skill_level = 'expert'
        WHERE skill_level = 'elite'
    """)

    # Step 2: Remove 'elite' from the skill_level enum
    # PostgreSQL doesn't support removing enum values directly,
    # so we need to rename the old type, create a new type, and update the columns

    # Rename the old enum type
    op.execute("""
        ALTER TYPE skilllevel RENAME TO skilllevel_old
    """)

    # Create the new enum type without 'elite'
    op.execute("""
        CREATE TYPE skilllevel AS ENUM (
            'beginner', 'intermediate', 'advanced', 'expert'
        )
    """)

    # Alter the columns to use the new enum type
    # Since we already updated all 'elite' values to 'expert', all values should be valid
    op.execute("""
        ALTER TABLE movements
        ALTER COLUMN skill_level TYPE skilllevel
        USING skill_level::text::skilllevel
    """)

    op.execute("""
        ALTER TABLE user_skills
        ALTER COLUMN skill_level TYPE skilllevel
        USING skill_level::text::skilllevel
    """)

    # Drop the old enum type
    op.execute("""
        DROP TYPE skilllevel_old
    """)


def downgrade() -> None:
    """Downgrade schema.

    Revert skill_level enum to include 'elite' value.
    Note: Data that was changed from 'elite' to 'expert' will remain 'expert'
    as we cannot distinguish which movements or user_skills were originally 'elite'.
    """

    # Rename the current enum type
    op.execute("""
        ALTER TYPE skilllevel RENAME TO skilllevel_new
    """)

    # Create the old enum type with 'elite' included
    op.execute("""
        CREATE TYPE skilllevel AS ENUM (
            'beginner', 'intermediate', 'advanced', 'expert', 'elite'
        )
    """)

    # Alter the columns to use the old enum type
    op.execute("""
        ALTER TABLE movements
        ALTER COLUMN skill_level TYPE skilllevel
        USING skill_level::text::skilllevel
    """)

    op.execute("""
        ALTER TABLE user_skills
        ALTER COLUMN skill_level TYPE skilllevel
        USING skill_level::text::skilllevel
    """)

    # Drop the new enum type
    op.execute("""
        DROP TYPE skilllevel_new
    """)
