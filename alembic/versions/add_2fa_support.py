from alembic import op
import sqlalchemy as sa


revision = 'add_2fa_support'
down_revision = 'add_refresh_tokens_table'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'two_factor_auths',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('secret', sa.String(length=32), nullable=False),
        sa.Column('backup_codes', sa.String(length=100), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_two_factor_auth_user_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_two_factor_auth_id'),
        sa.Index('ix_two_factor_auth_user_id', 'user_id'),
    )
    
    op.add_column(
        'users',
        sa.Column('admin_2fa_enabled', sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade():
    op.drop_index('ix_two_factor_auth_user_id', table_name='two_factor_auths')
    op.drop_table('two_factor_auths')
    op.drop_column('users', 'admin_2fa_enabled')
