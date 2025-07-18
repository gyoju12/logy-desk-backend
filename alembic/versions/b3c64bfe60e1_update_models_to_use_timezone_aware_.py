"""Update models to use timezone-aware datetimes

Revision ID: b3c64bfe60e1
Revises: cba74312cd02
Create Date: 2025-07-09 18:06:52.020696

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c64bfe60e1"
down_revision: Union[str, None] = "cba74312cd02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "agents",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "agents",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "chat_messages",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "chat_messages",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "chat_sessions",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "chat_sessions",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "document_chunks",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "document_chunks",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "documents",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "documents",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "users",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "users",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "users",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "users",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "documents",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "documents",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "document_chunks",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "document_chunks",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "chat_sessions",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "chat_sessions",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "chat_messages",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "chat_messages",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "agents",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "agents",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    # ### end Alembic commands ###
