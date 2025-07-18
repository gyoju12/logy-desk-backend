"""Add default system user

Revision ID: 6e4830d17465
Revises: ea811df5372c
Create Date: 2025-07-14 21:05:35.879928

"""
from datetime import datetime
from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from passlib.context import CryptContext

# revision identifiers, used by Alembic.
revision: str = '6e4830d17465'
down_revision: Union[str, None] = 'ea811df5372c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('agents', 'is_active',
               existing_type=sa.BOOLEAN(),
               server_default=None,
               existing_nullable=True)
    
    # Add default system user
    users_table = sa.table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True)),
        sa.Column('email', sa.String()),
        sa.Column('hashed_password', sa.String()),
        sa.Column('is_active', sa.Boolean()),
        sa.Column('is_superuser', sa.Boolean()),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True))
    )
    
    # Hash the default password
    hashed_password = pwd_context.hash("defaultpassword")
    
    # Insert the default system user
    op.bulk_insert(
        users_table,
        [
            {
                'id': UUID('00000000-0000-0000-0000-000000000000'),
                'email': 'system@logydesk.com',
                'hashed_password': hashed_password,
                'is_active': True,
                'is_superuser': True,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        ]
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('agents', 'is_active',
               existing_type=sa.BOOLEAN(),
               server_default=sa.text('true'),
               existing_nullable=True)
    
    # Remove the default system user
    op.execute(
        "DELETE FROM users WHERE id = '00000000-0000-0000-0000-000000000000'"
    )
    # ### end Alembic commands ###
