"""add api token_blocklist and device_token (app mobile)

Revision ID: e3f4a5b6c7d8
Revises: d2b3c4e5f6a7
Create Date: 2026-06-29

Tabelas de suporte à API REST do app mobile (/api/v1):
- token_blocklist: refresh tokens JWT revogados (logout / rotação).
- device_token: Expo push token por device.
Não altera nada do site Jinja existente.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3f4a5b6c7d8'
down_revision = 'd2b3c4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'token_blocklist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('jti', sa.String(length=36), nullable=False),
        sa.Column('token_type', sa.String(length=16), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jti'),
    )
    with op.batch_alter_table('token_blocklist', schema=None) as batch_op:
        batch_op.create_index('ix_token_blocklist_jti', ['jti'], unique=True)
        batch_op.create_index('ix_token_blocklist_created_at', ['created_at'], unique=False)

    op.create_table(
        'device_token',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('platform', sa.String(length=16), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )
    with op.batch_alter_table('device_token', schema=None) as batch_op:
        batch_op.create_index('ix_device_token_user_id', ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('device_token', schema=None) as batch_op:
        batch_op.drop_index('ix_device_token_user_id')
    op.drop_table('device_token')

    with op.batch_alter_table('token_blocklist', schema=None) as batch_op:
        batch_op.drop_index('ix_token_blocklist_created_at')
        batch_op.drop_index('ix_token_blocklist_jti')
    op.drop_table('token_blocklist')
