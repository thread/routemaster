"""
create trigger to sync updated field

Revision ID: 3eb4f3b419c6
Revises: 814a6b555eb9
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '3eb4f3b419c6'
down_revision = '814a6b555eb9'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        '''
        CREATE OR REPLACE FUNCTION sync_label_updated_column_fn()
            RETURNS TRIGGER AS
                $$
                    BEGIN
                        NEW.updated = now() AT TIME ZONE 'UTC';
                        RETURN NEW;
                    END;
                $$
            LANGUAGE PLPGSQL;

        CREATE TRIGGER sync_label_updated_column
            BEFORE UPDATE ON labels
            FOR EACH ROW
            EXECUTE PROCEDURE sync_label_updated_column_fn();
        ''',
    )


def downgrade():
    op.execute('DROP TRIGGER sync_label_updated_column')
    op.execute('DROP FUNCTION sync_label_updated_column_fn')
