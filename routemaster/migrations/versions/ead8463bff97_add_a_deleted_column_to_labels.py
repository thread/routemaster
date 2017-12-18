"""
Add a deleted column to labels

Revision ID: ead8463bff97
Revises: 4ff14db28f2d
"""
import sqlalchemy as sa

from alembic import op



# revision identifiers, used by Alembic.
revision = 'ead8463bff97'
down_revision = '4ff14db28f2d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('labels', sa.Column('deleted', sa.Boolean(), nullable=False))


def downgrade():
    op.drop_column('labels', 'deleted')
