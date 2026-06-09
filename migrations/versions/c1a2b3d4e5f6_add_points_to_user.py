"""add points (gamificação) to user

Revision ID: c1a2b3d4e5f6
Revises: 185f58bc7579
Create Date: 2026-06-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1a2b3d4e5f6'
down_revision = '185f58bc7579'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('points', sa.Integer(), nullable=False, server_default='0')
        )


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('points')
