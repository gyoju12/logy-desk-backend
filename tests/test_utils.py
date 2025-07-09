import json
from uuid import UUID
from typing import Any, Dict, Optional
from sqlalchemy.types import TypeDecorator, CHAR, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
import sqlalchemy as sa

class GUID(TypeDecorator):
    """
    Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(32), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, UUID):
                return str(UUID(value).hex)
            else:
                return value.hex

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        else:
            if not isinstance(value, UUID):
                value = UUID(value)
            return value

class JSONType(TypeDecorator):
    """Custom JSON type that works with SQLite."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Optional[Dict[str, Any]], dialect) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[Dict[str, Any]]:
        if value is None:
            return None
        return json.loads(value)

def patch_models_for_sqlite():
    """Patch SQLAlchemy models to use custom types for SQLite compatibility."""
    from app.models import db_models
    
    # Get all model classes
    models = [getattr(db_models, name) for name in dir(db_models) 
             if not name.startswith('_') and hasattr(getattr(db_models, name), '__table__')]
    
    for model in models:
        for column in model.__table__.columns:
            # Replace UUID columns
            if isinstance(column.type, sa.dialects.postgresql.UUID):
                column.type = GUID()
            # Replace JSONB columns
            elif isinstance(column.type, JSONB):
                column.type = JSONType()
