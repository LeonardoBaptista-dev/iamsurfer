"""
Migração para adicionar suporte a múltiplas URLs de imagem nos posts
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_multiple_image_urls'
down_revision = None  # Será definido automaticamente
branch_labels = None
depends_on = None

def upgrade():
    # Adiciona colunas para diferentes tamanhos de imagem
    op.add_column('post', sa.Column('image_urls', sa.JSON(), nullable=True))
    op.add_column('post', sa.Column('image_hash', sa.String(32), nullable=True))
    
    # Adiciona índice no hash para performance
    op.create_index('idx_post_image_hash', 'post', ['image_hash'])

def downgrade():
    # Remove índice
    op.drop_index('idx_post_image_hash', table_name='post')
    
    # Remove colunas
    op.drop_column('post', 'image_hash')
    op.drop_column('post', 'image_urls')
