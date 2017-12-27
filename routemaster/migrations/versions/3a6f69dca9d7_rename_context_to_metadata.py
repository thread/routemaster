"""
Rename context to metadata

Revision ID: 3a6f69dca9d7
Revises: 3ab04cd7bb80
"""
import sqlalchemy as sa

from alembic import op

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3a6f69dca9d7'
down_revision = '3ab04cd7bb80'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('labels', 'context', new_column_name='metadata')


def downgrade():
    op.alter_column('labels', 'metadata', new_column_name='context')
