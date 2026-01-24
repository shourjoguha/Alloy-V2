"""phase1_step1_add_tier_metabolic_demand_and_biomechanics_profile

Revision ID: 82c02a09d89a
Revises: ec60834536f3
Create Date: 2026-01-24 00:33:43.938323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '82c02a09d89a'
down_revision: Union[str, Sequence[str], None] = 'ec60834536f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    movement_tier_enum = sa.Enum('diamond', 'gold', 'silver', 'bronze', name='movementtier')
    movement_tier_enum.create(op.get_bind(), checkfirst=True)
    
    metabolic_demand_enum = sa.Enum('anabolic', 'metabolic', 'neural', name='metabolicdemand')
    metabolic_demand_enum.create(op.get_bind(), checkfirst=True)
    
    op.add_column('movements', sa.Column('tier', movement_tier_enum, nullable=False, server_default='bronze'))
    op.add_column('movements', sa.Column('metabolic_demand', metabolic_demand_enum, nullable=False, server_default='anabolic'))
    op.add_column('movements', sa.Column('biomechanics_profile', JSONB(), nullable=True))
    
    op.create_index('ix_movements_tier', 'movements', ['tier'])
    op.create_index('ix_movements_metabolic_demand', 'movements', ['metabolic_demand'])
    
    op.execute("CREATE INDEX ix_movements_biomechanics_profile_gin ON movements USING GIN (biomechanics_profile)")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_movements_biomechanics_profile_gin', table_name='movements')
    op.drop_index('ix_movements_metabolic_demand', table_name='movements')
    op.drop_index('ix_movements_tier', table_name='movements')
    
    op.drop_column('movements', 'biomechanics_profile')
    op.drop_column('movements', 'metabolic_demand')
    op.drop_column('movements', 'tier')
    
    sa.Enum(name='metabolicdemand').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='movementtier').drop(op.get_bind(), checkfirst=True)
