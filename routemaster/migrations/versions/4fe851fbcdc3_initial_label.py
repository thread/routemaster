"""
Initial label

Revision ID: 4fe851fbcdc3
Revises: 091a6e84d9ac
"""
import sqlalchemy as sa

from alembic import op

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4fe851fbcdc3'
down_revision = '091a6e84d9ac'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('labels',
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('state_machine', sa.String(), nullable=False),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('name', 'state_machine')
    )


def downgrade():
    op.drop_table('labels')
