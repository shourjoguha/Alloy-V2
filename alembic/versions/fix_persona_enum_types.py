"""fix_persona_enum_types

Revision ID: fix_persona_enum_types
Revises: ebaa3499c4af
Create Date: 2026-01-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_persona_enum_types'
down_revision: Union[str, Sequence[str], None] = 'add_favorites_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    
    Fix persona_tone and persona_aggression column types to match current enum definitions.
    - Update persona_tone from personatone_old to personatone
    - Update persona_aggression from personaaggression_old to personaaggression
    """
    
    # Update persona_tone column type with explicit value mapping (uppercase -> lowercase)
    op.execute("""
        ALTER TABLE programs 
        ALTER COLUMN persona_tone 
        TYPE personatone 
        USING CASE persona_tone::text
            WHEN 'DRILL_SERGEANT' THEN 'drill_sergeant'::personatone
            WHEN 'SUPPORTIVE' THEN 'supportive'::personatone
            WHEN 'ANALYTICAL' THEN 'analytical'::personatone
            WHEN 'MOTIVATIONAL' THEN 'motivational'::personatone
            WHEN 'MINIMALIST' THEN 'minimalist'::personatone
            ELSE 'supportive'::personatone
        END
    """)
    
    # Update persona_aggression column type with value mapping (string -> integer)
    op.execute("""
        ALTER TABLE programs 
        ALTER COLUMN persona_aggression 
        TYPE personaaggression 
        USING CASE persona_aggression::text
            WHEN 'CONSERVATIVE' THEN '1'::personaaggression
            WHEN 'MODERATE_CONSERVATIVE' THEN '2'::personaaggression
            WHEN 'BALANCED' THEN '3'::personaaggression
            WHEN 'MODERATE_AGGRESSIVE' THEN '4'::personaaggression
            WHEN 'AGGRESSIVE' THEN '5'::personaaggression
            ELSE '3'::personaaggression
        END
    """)


def downgrade() -> None:
    """Downgrade schema.
    
    Rollback persona enum type changes.
    """
    
    # Revert persona_tone column type with explicit value mapping (lowercase -> uppercase)
    op.execute("""
        ALTER TABLE programs 
        ALTER COLUMN persona_tone 
        TYPE personatone_old 
        USING CASE persona_tone::text
            WHEN 'drill_sergeant' THEN 'DRILL_SERGEANT'::personatone_old
            WHEN 'supportive' THEN 'SUPPORTIVE'::personatone_old
            WHEN 'analytical' THEN 'ANALYTICAL'::personatone_old
            WHEN 'motivational' THEN 'MOTIVATIONAL'::personatone_old
            WHEN 'minimalist' THEN 'MINIMALIST'::personatone_old
            ELSE 'SUPPORTIVE'::personatone_old
        END
    """)
    
    # Revert persona_aggression column type with value mapping (integer -> string)
    op.execute("""
        ALTER TABLE programs 
        ALTER COLUMN persona_aggression 
        TYPE personaaggression_old 
        USING CASE persona_aggression::text
            WHEN '1' THEN 'CONSERVATIVE'::personaaggression_old
            WHEN '2' THEN 'MODERATE_CONSERVATIVE'::personaaggression_old
            WHEN '3' THEN 'BALANCED'::personaaggression_old
            WHEN '4' THEN 'MODERATE_AGGRESSIVE'::personaaggression_old
            WHEN '5' THEN 'AGGRESSIVE'::personaaggression_old
            ELSE 'BALANCED'::personaaggression_old
        END
    """)
