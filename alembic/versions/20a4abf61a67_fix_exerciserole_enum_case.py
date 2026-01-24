"""fix exerciserole enum case

Revision ID: 20a4abf61a67
Revises: 662e6fe73056
Create Date: 2026-01-23 01:00:02.071885

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20a4abf61a67'
down_revision: Union[str, Sequence[str], None] = '662e6fe73056'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
    DO $$
    BEGIN
        -- Rename old enum
        IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'exerciserole') THEN
            ALTER TYPE exerciserole RENAME TO exerciserole_old;
        END IF;

        -- Create new enum
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'exerciserole') THEN
            CREATE TYPE exerciserole AS ENUM ('warmup', 'main', 'accessory', 'skill', 'finisher', 'cooldown', 'cardio', 'conditioning');
        END IF;
    END$$;
    """)

    # Alter column
    op.execute("""
    ALTER TABLE session_exercises 
    ALTER COLUMN role TYPE exerciserole 
    USING LOWER(role::text)::exerciserole;
    """)

    # Drop old enum
    op.execute("DROP TYPE IF EXISTS exerciserole_old")


def downgrade() -> None:
    """Downgrade schema."""
    # Revert to uppercase (simplified set)
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'exerciserole') THEN
            ALTER TYPE exerciserole RENAME TO exerciserole_new;
        END IF;

        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'exerciserole') THEN
            CREATE TYPE exerciserole AS ENUM ('WARMUP', 'MAIN', 'ACCESSORY', 'SKILL', 'FINISHER', 'COOLDOWN', 'CARDIO', 'CONDITIONING');
        END IF;
    END$$;
    """)
    
    op.execute("""
    ALTER TABLE session_exercises 
    ALTER COLUMN role TYPE exerciserole 
    USING UPPER(role::text)::exerciserole;
    """)
    
    op.execute("DROP TYPE IF EXISTS exerciserole_new")
