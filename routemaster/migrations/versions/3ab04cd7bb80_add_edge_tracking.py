"""
Add edge tracking

Revision ID: 3ab04cd7bb80
Revises: ead8463bff97
"""
import sqlalchemy as sa

from alembic import op



# revision identifiers, used by Alembic.
revision = '3ab04cd7bb80'
down_revision = 'ead8463bff97'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('edges',
        sa.Column('state_machine', sa.String(), nullable=False),
        sa.Column('from_state', sa.String(), nullable=False),
        sa.Column('to_state', sa.String(), nullable=False),
        sa.Column('deprecated', sa.Boolean(), nullable=False),
        sa.Column('updated', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['state_machine', 'from_state'], ['states.state_machine', 'states.name'], ),
        sa.ForeignKeyConstraint(['state_machine', 'to_state'], ['states.state_machine', 'states.name'], ),
        sa.PrimaryKeyConstraint('state_machine', 'from_state', 'to_state')
    )


def downgrade():
    op.drop_table('edges')
