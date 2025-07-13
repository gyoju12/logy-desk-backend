"""
This module provides backward compatibility by re-exporting models from db_models.
New code should import models directly from app.models.db_models.
"""

from app.models.db_models import (
    Agent,
    ChatMessage,
    ChatSession,
    Document,
    DocumentChunk,
    User,
)

__all__ = [
    "User",
    "Agent",
    "Document",
    "DocumentChunk",
    "ChatSession",
    "ChatMessage",
]
