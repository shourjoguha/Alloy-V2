"""fix_persona_tone_enum_values

Revision ID: e0787659d7a0
Revises: 89406d16608b
Create Date: 2026-01-26 02:11:01.023955

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0787659d7a0'
down_revision: Union[str, Sequence[str], None] = '89406d16608b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    
    Fix persona_tone enum type to use lowercase values.
    The PersonaTone Python enum uses lowercase values (drill_sergeant, supportive, etc.)
    but the database enum type was created with uppercase values (DRILL_SERGEANT, SUPPORTIVE, etc.).
    """
    
    # First, add temporary columns to hold the string values
    op.add_column('programs', sa.Column('persona_tone_temp', sa.String(), nullable=True))
    op.add_column('users', sa.Column('persona_tone_temp', sa.String(), nullable=True))
    
    # Convert existing uppercase values to lowercase in programs table
    op.execute("""
        UPDATE programs 
        SET persona_tone_temp = CASE persona_tone::text
            WHEN 'DRILL_SERGEANT' THEN 'drill_sergeant'
            WHEN 'SUPPORTIVE' THEN 'supportive'
            WHEN 'ANALYTICAL' THEN 'analytical'
            WHEN 'MOTIVATIONAL' THEN 'motivational'
            WHEN 'MINIMALIST' THEN 'minimalist'
            ELSE 'supportive'
        END
    """)
    
    # Convert existing uppercase values to lowercase in users table
    op.execute("""
        UPDATE users 
        SET persona_tone_temp = CASE persona_tone::text
            WHEN 'DRILL_SERGEANT' THEN 'drill_sergeant'
            WHEN 'SUPPORTIVE' THEN 'supportive'
            WHEN 'ANALYTICAL' THEN 'analytical'
            WHEN 'MOTIVATIONAL' THEN 'motivational'
            WHEN 'MINIMALIST' THEN 'minimalist'
            ELSE 'supportive'
        END
    """)
    
    # Drop the old enum type from both tables
    op.execute("ALTER TABLE programs DROP COLUMN persona_tone")
    op.execute("ALTER TABLE users DROP COLUMN persona_tone")
    op.execute("DROP TYPE personatone")
    
    # Create the new enum type with lowercase values
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE personatone AS ENUM (
                'drill_sergeant', 'supportive', 'analytical', 
                'motivational', 'minimalist'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Add the column back with the new enum type for programs table (nullable first)
    op.add_column('programs', sa.Column('persona_tone', sa.Enum('drill_sergeant', 'supportive', 'analytical', 'motivational', 'minimalist', name='personatone'), nullable=True))
    
    # Add the column back with the new enum type for users table (nullable first)
    op.add_column('users', sa.Column('persona_tone', sa.Enum('drill_sergeant', 'supportive', 'analytical', 'motivational', 'minimalist', name='personatone'), nullable=True))
    
    # Copy the values back from the temp columns
    op.execute("""
        UPDATE programs 
        SET persona_tone = persona_tone_temp::personatone
    """)
    
    op.execute("""
        UPDATE users 
        SET persona_tone = persona_tone_temp::personatone
    """)
    
    # Now make the columns NOT NULL
    op.execute("ALTER TABLE programs ALTER COLUMN persona_tone SET NOT NULL")
    op.execute("ALTER TABLE users ALTER COLUMN persona_tone SET NOT NULL")
    
    # Drop the temp columns
    op.drop_column('programs', 'persona_tone_temp')
    op.drop_column('users', 'persona_tone_temp')


def downgrade() -> None:
    """Downgrade schema.
    
    Revert persona_tone enum type back to uppercase values.
    """
    
    # Add temporary columns to hold the string values
    op.add_column('programs', sa.Column('persona_tone_temp', sa.String(), nullable=True))
    op.add_column('users', sa.Column('persona_tone_temp', sa.String(), nullable=True))
    
    # Convert existing lowercase values to uppercase in programs table
    op.execute("""
        UPDATE programs 
        SET persona_tone_temp = CASE persona_tone::text
            WHEN 'drill_sergeant' THEN 'DRILL_SERGEANT'
            WHEN 'supportive' THEN 'SUPPORTIVE'
            WHEN 'analytical' THEN 'ANALYTICAL'
            WHEN 'motivational' THEN 'MOTIVATIONAL'
            WHEN 'minimalist' THEN 'MINIMALIST'
            ELSE 'SUPPORTIVE'
        END
    """)
    
    # Convert existing lowercase values to uppercase in users table
    op.execute("""
        UPDATE users 
        SET persona_tone_temp = CASE persona_tone::text
            WHEN 'drill_sergeant' THEN 'DRILL_SERGEANT'
            WHEN 'supportive' THEN 'SUPPORTIVE'
            WHEN 'analytical' THEN 'ANALYTICAL'
            WHEN 'motivational' THEN 'MOTIVATIONAL'
            WHEN 'minimalist' THEN 'MINIMALIST'
            ELSE 'SUPPORTIVE'
        END
    """)
    
    # Drop the enum type from both tables
    op.execute("ALTER TABLE programs DROP COLUMN persona_tone")
    op.execute("ALTER TABLE users DROP COLUMN persona_tone")
    op.execute("DROP TYPE personatone")
    
    # Create the uppercase enum type
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE personatone AS ENUM (
                'DRILL_SERGEANT', 'SUPPORTIVE', 'ANALYTICAL', 
                'MOTIVATIONAL', 'MINIMALIST'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Add the column back with the uppercase enum type for programs table (nullable first)
    op.add_column('programs', sa.Column('persona_tone', sa.Enum('DRILL_SERGEANT', 'SUPPORTIVE', 'ANALYTICAL', 'MOTIVATIONAL', 'MINIMALIST', name='personatone'), nullable=True))
    
    # Add the column back with the uppercase enum type for users table (nullable first)
    op.add_column('users', sa.Column('persona_tone', sa.Enum('DRILL_SERGEANT', 'SUPPORTIVE', 'ANALYTICAL', 'MOTIVATIONAL', 'MINIMALIST', name='personatone'), nullable=True))
    
    # Copy the values back from the temp columns
    op.execute("""
        UPDATE programs 
        SET persona_tone = persona_tone_temp::personatone
    """)
    
    op.execute("""
        UPDATE users 
        SET persona_tone = persona_tone_temp::personatone
    """)
    
    # Now make the columns NOT NULL
    op.execute("ALTER TABLE programs ALTER COLUMN persona_tone SET NOT NULL")
    op.execute("ALTER TABLE users ALTER COLUMN persona_tone SET NOT NULL")
    
    # Drop the temp columns
    op.drop_column('programs', 'persona_tone_temp')
    op.drop_column('users', 'persona_tone_temp')
