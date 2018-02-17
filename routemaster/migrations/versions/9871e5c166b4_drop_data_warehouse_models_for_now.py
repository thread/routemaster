"""
drop data warehouse models for now

Revision ID: 9871e5c166b4
Revises: 3eb4f3b419c6
"""
import sqlalchemy as sa

from alembic import op

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9871e5c166b4'
down_revision = '3eb4f3b419c6'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('edges')
    op.drop_table('states')
    op.drop_table('state_machines')


def downgrade():
    op.create_table(
        'states',
        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column(
            'state_machine',
            sa.VARCHAR(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'deprecated',
            sa.BOOLEAN(),
            server_default=sa.text('false'),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'updated',
            postgresql.TIMESTAMP(),
            server_default=sa.text('now()'),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['state_machine'],
            ['state_machines.name'],
            name='states_state_machine_fkey',
        ),
        sa.PrimaryKeyConstraint('name', 'state_machine', name='states_pkey'),
        postgresql_ignore_search_path=False,
    )
    op.create_table(
        'state_machines',
        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column(
            'updated',
            postgresql.TIMESTAMP(),
            server_default=sa.text('now()'),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('name', name='state_machines_pkey'),
        postgresql_ignore_search_path=False,
    )
    op.create_table(
        'edges',
        sa.Column(
            'state_machine',
            sa.VARCHAR(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'from_state',
            sa.VARCHAR(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'to_state',
            sa.VARCHAR(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'deprecated',
            sa.BOOLEAN(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'updated',
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['state_machine', 'from_state'],
            ['states.state_machine', 'states.name'],
            name='edges_state_machine_fkey',
        ),
        sa.ForeignKeyConstraint(
            ['state_machine', 'to_state'],
            ['states.state_machine', 'states.name'],
            name='edges_state_machine_fkey1',
        ),
        sa.PrimaryKeyConstraint(
            'state_machine',
            'from_state',
            'to_state',
            name='edges_pkey',
        ),
    )
