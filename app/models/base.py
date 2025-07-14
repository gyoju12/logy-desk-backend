from datetime import datetime
from typing import Any, Dict
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Mapped, mapped_column


@as_declarative()
class BaseModel:
    """Base model class that includes common fields and methods."""

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        # Using self.__dict__ for simplicity, consider inspect(self).mapper.columns for more robust solution
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def update(self, **kwargs: Any) -> None:
        """Update model instance with given attributes."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"