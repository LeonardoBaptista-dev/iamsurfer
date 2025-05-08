"""add destination text field

Revision ID: add_destination_text
Create Date: 2023-05-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_destination_text'
down_revision = None  # Será preenchido automaticamente

branch_labels = None
depends_on = None

def upgrade():
    # Adicionar nova coluna destination_text (nome diferente para evitar conflitos)
    op.add_column('surf_trip', sa.Column('destination_text', sa.String(100), nullable=True))
    
    # Preencher a nova coluna com dados dos spots existentes
    op.execute(
        """
        UPDATE surf_trip 
        SET destination_text = (
            SELECT surf_spot.name || ', ' || surf_spot.location 
            FROM surf_spot 
            WHERE surf_spot.id = surf_trip.destination_id
        )
        WHERE destination_id IS NOT NULL
        """
    )

def downgrade():
    # Remover a coluna destination_text
    op.drop_column('surf_trip', 'destination_text')