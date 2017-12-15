"""
Initial state machine

Revision ID: 091a6e84d9ac
Revises: 
"""
import sqlalchemy as sa

from alembic import op

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '091a6e84d9ac'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('state_machines',
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('name'),
    )
    op.create_table('states',
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('state_machine', sa.String(), nullable=False),
        sa.Column('deprecated', sa.Boolean(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['state_machine'], ['state_machines.name'], ),
        sa.PrimaryKeyConstraint('name', 'state_machine'),
    )


def downgrade():
    op.drop_table('states')
    op.drop_table('state_machines')
