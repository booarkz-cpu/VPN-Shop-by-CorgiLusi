"""Previewed customer operations and durable import deduplication."""
from alembic import op
import sqlalchemy as sa

revision = '0058_customer_operations'
down_revision = '0057_partner_commissions'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('customer_operations',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('actor', sa.String(320), nullable=False),
        sa.Column('kind', sa.String(16), nullable=False),
        sa.Column('reason', sa.String(500), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('fingerprint', sa.String(64), nullable=False),
        sa.Column('result', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('applied_at', sa.DateTime()))
    op.create_index('ix_customer_operations_actor', 'customer_operations', ['actor'])
    op.create_table('user_import_identities',
        sa.Column('telegram_id', sa.BigInteger(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('operation_id', sa.String(64), sa.ForeignKey('customer_operations.id', ondelete='RESTRICT'), nullable=False))


def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('LOCK TABLE customer_operations, user_import_identities IN ACCESS EXCLUSIVE MODE')
    if op.get_bind().execute(sa.text("SELECT 1 FROM customer_operations WHERE status='applied' LIMIT 1")).first():
        raise RuntimeError('Applied customer operations require coordinated backup restore, not downgrade')
    op.drop_table('user_import_identities')
    op.drop_index('ix_customer_operations_actor', 'customer_operations')
    op.drop_table('customer_operations')
