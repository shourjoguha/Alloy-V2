"""fix_persona_aggression_integer_enum

Revision ID: 89406d16608b
Revises: 38a5628f9650
Create Date: 2026-01-26 02:01:46.364031

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89406d16608b'
down_revision: Union[str, Sequence[str], None] = '38a5628f9650'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    
    Fix persona_aggression enum type to use the correct enum names.
    The PersonaAggression Python enum is an int enum, but PostgreSQL enums are always strings.
    SQLAlchemy stores the enum as the enum names (CONSERVATIVE, BALANCED, etc.) not the integer values.
    """
    
    # First, add temporary columns to hold the string values
    op.add_column('programs', sa.Column('persona_aggression_temp', sa.String(), nullable=True))
    op.add_column('users', sa.Column('persona_aggression_temp', sa.String(), nullable=True))
    
    # Convert existing values to the correct enum names in programs table
    op.execute("""
        UPDATE programs 
        SET persona_aggression_temp = CASE persona_aggression::text
            WHEN '1' THEN 'CONSERVATIVE'
            WHEN '2' THEN 'MODERATE_CONSERVATIVE'
            WHEN '3' THEN 'BALANCED'
            WHEN '4' THEN 'MODERATE_AGGRESSIVE'
            WHEN '5' THEN 'AGGRESSIVE'
            ELSE 'BALANCED'
        END
    """)
    
    # Convert existing values to the correct enum names in users table
    op.execute("""
        UPDATE users 
        SET persona_aggression_temp = CASE persona_aggression::text
            WHEN '1' THEN 'CONSERVATIVE'
            WHEN '2' THEN 'MODERATE_CONSERVATIVE'
            WHEN '3' THEN 'BALANCED'
            WHEN '4' THEN 'MODERATE_AGGRESSIVE'
            WHEN '5' THEN 'AGGRESSIVE'
            ELSE 'BALANCED'
        END
    """)
    
    # Drop the old enum type from both tables
    op.execute("ALTER TABLE programs DROP COLUMN persona_aggression")
    op.execute("ALTER TABLE users DROP COLUMN persona_aggression")
    op.execute("DROP TYPE personaaggression")
    
    # Create the new enum type with the correct enum names
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE personaaggression AS ENUM (
                'CONSERVATIVE', 'MODERATE_CONSERVATIVE', 'BALANCED', 
                'MODERATE_AGGRESSIVE', 'AGGRESSIVE'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Add the column back with the new enum type for programs table (nullable first)
    op.add_column('programs', sa.Column('persona_aggression', sa.Enum('CONSERVATIVE', 'MODERATE_CONSERVATIVE', 'BALANCED', 'MODERATE_AGGRESSIVE', 'AGGRESSIVE', name='personaaggression'), nullable=True))
    
    # Add the column back with the new enum type for users table (nullable first)
    op.add_column('users', sa.Column('persona_aggression', sa.Enum('CONSERVATIVE', 'MODERATE_CONSERVATIVE', 'BALANCED', 'MODERATE_AGGRESSIVE', 'AGGRESSIVE', name='personaaggression'), nullable=True))
    
    # Copy the values back from the temp columns
    op.execute("""
        UPDATE programs 
        SET persona_aggression = persona_aggression_temp::personaaggression
    """)
    
    op.execute("""
        UPDATE users 
        SET persona_aggression = persona_aggression_temp::personaaggression
    """)
    
    # Now make the columns NOT NULL
    op.execute("ALTER TABLE programs ALTER COLUMN persona_aggression SET NOT NULL")
    op.execute("ALTER TABLE users ALTER COLUMN persona_aggression SET NOT NULL")
    
    # Drop the temp columns
    op.drop_column('programs', 'persona_aggression_temp')
    op.drop_column('users', 'persona_aggression_temp')


def downgrade() -> None:
    """Downgrade schema.
    
    Revert persona_aggression enum type back to integer string values.
    """
    
    # Add temporary columns to hold the string values
    op.add_column('programs', sa.Column('persona_aggression_temp', sa.String(), nullable=True))
    op.add_column('users', sa.Column('persona_aggression_temp', sa.String(), nullable=True))
    
    # Convert existing enum names to integer string values in programs table
    op.execute("""
        UPDATE programs 
        SET persona_aggression_temp = CASE persona_aggression::text
            WHEN 'CONSERVATIVE' THEN '1'
            WHEN 'MODERATE_CONSERVATIVE' THEN '2'
            WHEN 'BALANCED' THEN '3'
            WHEN 'MODERATE_AGGRESSIVE' THEN '4'
            WHEN 'AGGRESSIVE' THEN '5'
            ELSE '3'
        END
    """)
    
    # Convert existing enum names to integer string values in users table
    op.execute("""
        UPDATE users 
        SET persona_aggression_temp = CASE persona_aggression::text
            WHEN 'CONSERVATIVE' THEN '1'
            WHEN 'MODERATE_CONSERVATIVE' THEN '2'
            WHEN 'BALANCED' THEN '3'
            WHEN 'MODERATE_AGGRESSIVE' THEN '4'
            WHEN 'AGGRESSIVE' THEN '5'
            ELSE '3'
        END
    """)
    
    # Drop the enum type from both tables
    op.execute("ALTER TABLE programs DROP COLUMN persona_aggression")
    op.execute("ALTER TABLE users DROP COLUMN persona_aggression")
    op.execute("DROP TYPE personaaggression")
    
    # Create the integer string enum type
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE personaaggression AS ENUM (
                '1', '2', '3', '4', '5'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Add the column back with the integer string enum type for programs table (nullable first)
    op.add_column('programs', sa.Column('persona_aggression', sa.Enum('1', '2', '3', '4', '5', name='personaaggression'), nullable=True))
    
    # Add the column back with the integer string enum type for users table (nullable first)
    op.add_column('users', sa.Column('persona_aggression', sa.Enum('1', '2', '3', '4', '5', name='personaaggression'), nullable=True))
    
    # Copy the values back from the temp columns
    op.execute("""
        UPDATE programs 
        SET persona_aggression = persona_aggression_temp::personaaggression
    """)
    
    op.execute("""
        UPDATE users 
        SET persona_aggression = persona_aggression_temp::personaaggression
    """)
    
    # Now make the columns NOT NULL
    op.execute("ALTER TABLE programs ALTER COLUMN persona_aggression SET NOT NULL")
    op.execute("ALTER TABLE users ALTER COLUMN persona_aggression SET NOT NULL")
    
    # Drop the temp columns
    op.drop_column('programs', 'persona_aggression_temp')
    op.drop_column('users', 'persona_aggression_temp')
