"""Add all changes

Revision ID: add_all_changes
Revises: b8143638a4dd
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_all_changes'
down_revision = 'b8143638a4dd'
branch_labels = None
depends_on = None

def upgrade():
    # Criar tabela state
    op.create_table('state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('uf', sa.String(length=2), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uf')
    )

    # Criar tabela city
    op.create_table('city',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('state_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['state_id'], ['state.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Adicionar colunas à tabela surf_spot
    op.add_column('surf_spot',
        sa.Column('city_id', sa.Integer(), nullable=True)
    )
    op.add_column('surf_spot',
        sa.Column('wave_type', sa.String(length=50), nullable=True)
    )
    op.add_column('surf_spot',
        sa.Column('difficulty_level', sa.String(length=20), nullable=True)
    )
    op.create_foreign_key(None, 'surf_spot', 'city', ['city_id'], ['id'])

    # Criar tabela photographer
    op.create_table('photographer',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('spot_id', sa.Integer(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('subscription_status', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['spot_id'], ['surf_spot.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Criar tabela spot_photo
    op.create_table('spot_photo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('spot_id', sa.Integer(), nullable=False),
        sa.Column('photographer_id', sa.Integer(), nullable=False),
        sa.Column('image_url', sa.String(length=255), nullable=False),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('is_for_sale', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['photographer_id'], ['photographer.id'], ),
        sa.ForeignKeyConstraint(['spot_id'], ['surf_spot.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Adicionar colunas de selos ao usuário
    op.add_column('user',
        sa.Column('is_pro_athlete', sa.Boolean(), nullable=True)
    )
    op.add_column('user',
        sa.Column('is_influencer', sa.Boolean(), nullable=True)
    )
    op.add_column('user',
        sa.Column('influencer_subscription', sa.String(length=20), nullable=True)
    )
    op.add_column('user',
        sa.Column('is_photographer', sa.Boolean(), nullable=True)
    )
    op.add_column('user',
        sa.Column('photographer_subscription', sa.String(length=20), nullable=True)
    )
    op.add_column('user',
        sa.Column('is_local_business', sa.Boolean(), nullable=True)
    )
    op.add_column('user',
        sa.Column('business_subscription', sa.String(length=20), nullable=True)
    )
    op.add_column('user',
        sa.Column('is_service_provider', sa.Boolean(), nullable=True)
    )
    op.add_column('user',
        sa.Column('service_provider_subscription', sa.String(length=20), nullable=True)
    )

def downgrade():
    # Remover colunas de selos do usuário
    op.drop_column('user', 'service_provider_subscription')
    op.drop_column('user', 'is_service_provider')
    op.drop_column('user', 'business_subscription')
    op.drop_column('user', 'is_local_business')
    op.drop_column('user', 'photographer_subscription')
    op.drop_column('user', 'is_photographer')
    op.drop_column('user', 'influencer_subscription')
    op.drop_column('user', 'is_influencer')
    op.drop_column('user', 'is_pro_athlete')

    # Remover tabela spot_photo
    op.drop_table('spot_photo')

    # Remover tabela photographer
    op.drop_table('photographer')

    # Remover colunas da tabela surf_spot
    op.drop_constraint(None, 'surf_spot', type_='foreignkey')
    op.drop_column('surf_spot', 'difficulty_level')
    op.drop_column('surf_spot', 'wave_type')
    op.drop_column('surf_spot', 'city_id')

    # Remover tabela city
    op.drop_table('city')

    # Remover tabela state
    op.drop_table('state')

