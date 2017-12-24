"""
Rename context io metadata

Revision ID: 3a6f69dca9d7
Revises: 4ff14db28f2d
"""
import sqlalchemy as sa

from alembic import op

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3a6f69dca9d7'
down_revision = '4ff14db28f2d'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('labels', 'context', new_column_name='metadata')


def downgrade():
    op.alter_column('labels', 'metadata', new_column_name='context')
