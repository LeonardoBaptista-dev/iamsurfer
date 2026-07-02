"""add payment fields to photo_purchase (app mobile A9)

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-01

Adiciona os campos de pagamento à tabela `photo_purchase` para o fluxo de
fotos à venda da API REST (/api/v1):
- provider: provedor de pagamento ('mercadopago' | 'test').
- provider_ref: referência externa (preference/payment id) para reconciliação
  pelo webhook. Indexado.
- coupon_code: cupom de desconto aplicado, se houver.
Não altera nada do site Jinja existente.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4a5b6c7d8e9'
down_revision = 'e3f4a5b6c7d8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('photo_purchase', schema=None) as batch_op:
        batch_op.add_column(sa.Column('provider', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('provider_ref', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('coupon_code', sa.String(length=40), nullable=True))
        batch_op.create_index('ix_photo_purchase_provider_ref', ['provider_ref'], unique=False)


def downgrade():
    with op.batch_alter_table('photo_purchase', schema=None) as batch_op:
        batch_op.drop_index('ix_photo_purchase_provider_ref')
        batch_op.drop_column('coupon_code')
        batch_op.drop_column('provider_ref')
        batch_op.drop_column('provider')
