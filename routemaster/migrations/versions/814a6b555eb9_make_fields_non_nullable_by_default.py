"""
make fields non-nullable by default

Revision ID: 814a6b555eb9
Revises: e7d5ad06c0d1
"""
import sqlalchemy as sa

from alembic import op

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '814a6b555eb9'
down_revision = 'e7d5ad06c0d1'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'history',
        'label_name',
        existing_type=sa.VARCHAR(),
        nullable=False,
    )
    op.alter_column(
        'history',
        'label_state_machine',
        existing_type=sa.VARCHAR(),
        nullable=False,
    )

    def set_not_null(table, column, existing_type, server_default):
        op.alter_column(
            table,
            column,
            existing_type=existing_type,
            server_default=server_default,
        )
        op.execute(
            f"UPDATE {table} SET {column} = {server_default} "
            f"WHERE {column} IS NULL",
        )
        op.alter_column(
            table,
            column,
            existing_type=existing_type,
            nullable=False,
        )

    set_not_null(
        'history',
        'created',
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.func.now(),
    )
    set_not_null(
        'history',
        'forced',
        existing_type=sa.BOOLEAN(),
        server_default=sa.false(),
    )
    set_not_null(
        'labels',
        'metadata',
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text("'{}'::json"),  # noqa
    )
    set_not_null(
        'labels',
        'metadata_triggers_processed',
        existing_type=sa.BOOLEAN(),
        server_default=sa.true(),
    )
    set_not_null(
        'state_machines',
        'updated',
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.func.now(),
    )
    set_not_null(
        'states',
        'deprecated',
        existing_type=sa.BOOLEAN(),
        server_default=sa.false(),
    )
    set_not_null(
        'states',
        'updated',
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.func.now(),
    )


def downgrade():
    op.alter_column(
        'states',
        'updated',
        existing_type=postgresql.TIMESTAMP(),
        nullable=True,
    )
    op.alter_column(
        'states',
        'deprecated',
        existing_type=sa.BOOLEAN(),
        nullable=True,
    )
    op.alter_column(
        'state_machines',
        'updated',
        existing_type=postgresql.TIMESTAMP(),
        nullable=True,
    )
    op.alter_column(
        'labels',
        'metadata_triggers_processed',
        existing_type=sa.BOOLEAN(),
        nullable=True,
    )
    op.alter_column(
        'labels',
        'metadata',
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )
    op.alter_column(
        'history',
        'label_state_machine',
        existing_type=sa.VARCHAR(),
        nullable=True,
    )
    op.alter_column(
        'history',
        'label_name',
        existing_type=sa.VARCHAR(),
        nullable=True,
    )
    op.alter_column(
        'history',
        'forced',
        existing_type=sa.BOOLEAN(),
        nullable=True,
    )
    op.alter_column(
        'history',
        'created',
        existing_type=postgresql.TIMESTAMP(),
        nullable=True,
    )
