"""
Initial history

Revision ID: 3d0b226940eb
Revises: 4fe851fbcdc3
"""
import sqlalchemy as sa

from alembic import op



# revision identifiers, used by Alembic.
revision = '3d0b226940eb'
down_revision = '4fe851fbcdc3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('label_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('label_name', sa.String(), nullable=True),
        sa.Column('label_state_machine', sa.String(), nullable=True),
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('forced', sa.Boolean(), nullable=True),
        sa.Column('old_state', sa.String(), nullable=True),
        sa.Column('new_state', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['label_name', 'label_state_machine'], ['labels.name', 'labels.state_machine'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('label_history')
