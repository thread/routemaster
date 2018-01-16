"""
add updated field to label

Revision ID: e7d5ad06c0d1
Revises: e1fec9622785
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = 'e7d5ad06c0d1'
down_revision = 'e1fec9622785'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'labels',
        sa.Column(
            'updated',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade():
    op.drop_column('labels', 'updated')
