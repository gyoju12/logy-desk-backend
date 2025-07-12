from fastapi import APIRouter
from .endpoints.agents import router as agents_router
from .endpoints.documents import router as documents_router
from .endpoints.chat_sessions import router as chat_sessions_router
from .endpoints.chat import router as chat_router

# Create main API router
api_router = APIRouter()

# Include all API routes with their respective prefixes and tags
api_router.include_router(agents_router, prefix="/agents", tags=["Agents"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(chat_sessions_router, prefix="/chat_sessions", tags=["Chat Sessions"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
