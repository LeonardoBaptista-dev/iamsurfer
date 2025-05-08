"""merge multiple heads

Revision ID: 1dca021ae18e
Revises: 8f6e336f3deb, add_destination_text
Create Date: 2025-05-08 00:25:21.637557

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1dca021ae18e'
down_revision = ('8f6e336f3deb', 'add_destination_text')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
