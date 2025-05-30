"""Automatic migration

Revision ID: 8f6e336f3deb
Revises: af775b745413
Create Date: 2025-05-06 21:01:45.701368

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f6e336f3deb'
down_revision = 'af775b745413'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('surf_trip',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('creator_id', sa.Integer(), nullable=False),
    sa.Column('departure_location', sa.String(length=100), nullable=False),
    sa.Column('destination_id', sa.Integer(), nullable=False),
    sa.Column('departure_time', sa.DateTime(), nullable=False),
    sa.Column('return_time', sa.DateTime(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('available_seats', sa.Integer(), nullable=False),
    sa.Column('contribution', sa.Float(), nullable=True),
    sa.Column('vehicle_info', sa.String(length=100), nullable=True),
    sa.Column('intermediate_stops', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['creator_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['destination_id'], ['surf_spot.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('trip_participant',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('trip_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('request_time', sa.DateTime(), nullable=True),
    sa.Column('confirmation_time', sa.DateTime(), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['trip_id'], ['surf_trip.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('trip_id', 'user_id', name='_trip_user_uc')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('trip_participant')
    op.drop_table('surf_trip')
    # ### end Alembic commands ###
