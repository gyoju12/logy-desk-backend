"""Increase document columns length

Revision ID: 2025_07_10_0812
Revises: 
Create Date: 2025-07-10 08:12:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_07_10_0812'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Increase file_name column length to 255
    op.alter_column('documents', 'file_name',
                   existing_type=sa.String(length=50),
                   type_=sa.String(length=255),
                   existing_nullable=False)
    
    # Increase file_path column length to 512
    op.alter_column('documents', 'file_path',
                   existing_type=sa.String(length=255),
                   type_=sa.String(length=512),
                   existing_nullable=False)


def downgrade():
    # Revert file_path column length back to 255
    op.alter_column('documents', 'file_path',
                   existing_type=sa.String(length=512),
                   type_=sa.String(length=255),
                   existing_nullable=False)
    
    # Revert file_name column length back to 50
    op.alter_column('documents', 'file_name',
                   existing_type=sa.String(length=255),
                   type_=sa.String(length=50),
                   existing_nullable=False)
