"""
Rename labels table

Revision ID: 4ff14db28f2d
Revises: 3d0b226940eb
"""
import sqlalchemy as sa

from alembic import op

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4ff14db28f2d'
down_revision = '3d0b226940eb'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('label_history', 'history')


def downgrade():
    op.rename_table('history', 'label_history')
