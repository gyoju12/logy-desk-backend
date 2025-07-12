"""fix_agent_type_enum_case_sensitivity

Revision ID: ea811df5372c
Revises: 6fbd90d378bc
Create Date: 2025-07-13 00:18:02.416844

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ea811df5372c'
down_revision: Union[str, None] = '6fbd90d378bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a temporary type to convert to text first
    op.execute("""
        ALTER TABLE agents 
        ALTER COLUMN agent_type TYPE TEXT 
        USING agent_type::TEXT;
    """)
    
    # Drop the old enum type
    op.execute("DROP TYPE IF EXISTS agenttype")
    
    # Create new enum type with lowercase values
    op.execute("CREATE TYPE agenttype AS ENUM ('main', 'sub')")
    
    # Convert the text values to the new enum type
    op.execute("""
        UPDATE agents 
        SET agent_type = LOWER(agent_type)
        WHERE agent_type IS NOT NULL;
        
        ALTER TABLE agents 
        ALTER COLUMN agent_type TYPE agenttype 
        USING agent_type::agenttype;
    """)


def downgrade() -> None:
    # This is a one-way migration to fix data consistency
    # No downgrade path is provided as we want to maintain lowercase values
    pass
