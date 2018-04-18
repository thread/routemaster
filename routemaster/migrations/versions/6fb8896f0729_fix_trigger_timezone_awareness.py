"""
fix trigger timezone awareness

Revision ID: 6fb8896f0729
Revises: ab899b70c758
"""
import sqlalchemy as sa

from alembic import op



# revision identifiers, used by Alembic.
revision = '6fb8896f0729'
down_revision = 'ab899b70c758'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        '''
        CREATE OR REPLACE FUNCTION sync_label_updated_column_fn()
            RETURNS TRIGGER AS
                $$
                    BEGIN
                        NEW.updated = now();
                        RETURN NEW;
                    END;
                $$
            LANGUAGE PLPGSQL;
        ''',
    )


def downgrade():
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
        ''',
    )
