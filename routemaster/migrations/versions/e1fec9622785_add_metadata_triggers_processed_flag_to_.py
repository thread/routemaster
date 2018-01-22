"""
add metadata_triggers_processed flag to labels

Revision ID: e1fec9622785
Revises: 3a6f69dca9d7
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = 'e1fec9622785'
down_revision = '3a6f69dca9d7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'labels',
        sa.Column('metadata_triggers_processed', sa.Boolean()),
    )


def downgrade():
    op.drop_column('labels', 'metadata_triggers_processed')
