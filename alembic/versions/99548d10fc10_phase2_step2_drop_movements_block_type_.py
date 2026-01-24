"""phase2_step2_drop_movements_block_type_column

Revision ID: 99548d10fc10
Revises: d85b37d662b7
Create Date: 2026-01-23 18:21:59.152882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99548d10fc10'
down_revision: Union[str, Sequence[str], None] = 'd85b37d662b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('movements', 'block_type')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('movements', sa.Column('block_type', sa.String(50), nullable=False, server_default='All'))
    op.execute("""
        UPDATE movements 
        SET block_type = 'All'
    """)
