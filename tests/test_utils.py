import json
from typing import Any, Dict, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import CHAR, Text, TypeDecorator


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(32),
    storing as stringified hex values.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value: Optional[UUID], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, UUID):
                return str(UUID(value))
            else:
                return str(value)

    def process_result_value(
        self, value: Optional[str], dialect: Any
    ) -> Optional[UUID]:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(value)
        except (ValueError, TypeError):
            return None


class JSONType(TypeDecorator):
    """Custom JSON type that works with SQLite."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(
        self, value: Optional[Dict[str, Any]], dialect: Any
    ) -> Optional[str]:
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(
        self, value: Optional[str], dialect: Any
    ) -> Optional[Dict[str, Any]]:
        if value is not None:
            try:
                return Dict[str, Any](
                    json.loads(value)
                )  # Explicitly cast to Dict[str, Any]
            except json.JSONDecodeError:
                return None
        return None


def patch_models_for_sqlite() -> None:
    """Patch SQLAlchemy models to use custom types for SQLite compatibility."""
    from app.models import db_models

    # Get all model classes
    models = [
        getattr(db_models, name)
        for name in dir(db_models)
        if not name.startswith("_") and hasattr(getattr(db_models, name), "__table__")
    ]

    for model in models:
        for column in model.__table__.columns:
            # Replace UUID columns
            if isinstance(column.type, sa.dialects.postgresql.UUID):
                column.type = GUID()
            # Replace JSONB columns
            elif isinstance(column.type, JSONB):
                column.type = JSONType()
