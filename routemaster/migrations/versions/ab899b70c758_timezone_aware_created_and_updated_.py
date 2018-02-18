"""
timezone aware created and updated fields

Revision ID: ab899b70c758
Revises: 9871e5c166b4
"""
import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = 'ab899b70c758'
down_revision = '9871e5c166b4'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        '''
        ALTER TABLE "history"
            ALTER COLUMN "created" TYPE timestamp with time zone,
            ALTER COLUMN "created" SET DEFAULT now() AT TIME ZONE 'UTC';

        ALTER TABLE "labels"
            ALTER COLUMN "updated" TYPE timestamp with time zone,
            ALTER COLUMN "updated" SET DEFAULT now() AT TIME ZONE 'UTC';
        ''',
    )


def downgrade():
    op.execute(
        '''
        ALTER TABLE "history"
            ALTER COLUMN "created" TYPE timestamp without time zone,
            ALTER COLUMN "created" SET DEFAULT now();

        ALTER TABLE "labels"
            ALTER COLUMN "updated" TYPE timestamp without time zone,
            ALTER COLUMN "updated" SET DEFAULT now();
        ''',
    )
