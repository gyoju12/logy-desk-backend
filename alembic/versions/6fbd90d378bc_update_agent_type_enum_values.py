"""update_agent_type_enum_values

Revision ID: 6fbd90d378bc
Revises: 8a132099c50f
Create Date: 2025-07-12 23:54:08.625801

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "6fbd90d378bc"
down_revision: Union[str, None] = "8a132099c50f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define the old and new enum types
old_agent_type_enum = postgresql.ENUM("MAIN", "SUB", name="agenttype")
new_agent_type_enum = postgresql.ENUM("main", "sub", name="agenttype")


def upgrade() -> None:
    # Create a temporary type to convert to text first
    op.execute("ALTER TYPE agenttype RENAME TO agenttype_old")

    # Create new enum type
    new_agent_type_enum.create(op.get_bind())

    # Update the column to use the new type
    op.execute(
        """
        ALTER TABLE agents 
        ALTER COLUMN agent_type TYPE agenttype 
        USING agent_type::text::agenttype
    """
    )

    # Drop the old type
    op.execute("DROP TYPE agenttype_old")


def downgrade() -> None:
    # Convert back to old type
    op.execute("ALTER TYPE agenttype RENAME TO agenttype_new")

    # Create old enum type
    old_agent_type_enum.create(op.get_bind())

    # Update the column to use the old type
    op.execute(
        """
        ALTER TABLE agents 
        ALTER COLUMN agent_type TYPE agenttype 
        USING agent_type::text::agenttype
    """
    )

    # Drop the new type
    op.execute("DROP TYPE agenttype_new")
