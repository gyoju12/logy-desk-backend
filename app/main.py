from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any, List, Optional

from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse, HTMLResponse # Added HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession # Changed import
from sqlalchemy.orm import Session # Keep Session for legacy_list_agents in main.py

# Import API routers
from app.api.router import api_router
from app.crud import crud_agent
from app.db.session import get_db

# API version
API_PREFIX = "/api/v1"


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]: # Added return type
    # Startup: Initialize resources (DB connections, etc.)
    print("Starting up...")

    yield

    # Shutdown: Clean up resources
    print("Shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="Logy-Desk API",
    description="Logy-Desk Backend API Documentation",
    version="1.0.0",
    docs_url=None,  # Disable default docs to customize
    redoc_url=None,  # Disable default redoc
    openapi_url=f"{API_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root router
root_router = APIRouter()


# Health check endpoint
@root_router.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check() -> Dict[str, str]: # Added return type
    """Health check endpoint for monitoring"""
    return {"status": "healthy"}


# 레거시 API 호환성을 위한 라우터
legacy_router = APIRouter()


@legacy_router.get("/agents", include_in_schema=False)
async def legacy_list_agents(type: Optional[str] = None, db: AsyncSession = Depends(get_db)) -> List[Any]: # Changed type to Optional[str], db to AsyncSession, added return type
    """
    레거시 엔드포인트: /api/agents

    - type: 필터링할 에이전트 유형 (main, sub)
    """
    agents = await crud_agent.agent.get_multi(db)
    if type in ["main", "sub"]:
        agents = [a for a in agents if a.agent_type == type]
    return agents


@legacy_router.get("/chats", include_in_schema=False)
async def legacy_list_chats(db: AsyncSession = Depends(get_db)) -> List[Any]: # Changed db to AsyncSession, added return type
    """
    레거시 엔드포인트: /api/chats

    현재는 빈 배열을 반환합니다.
    실제 구현이 필요하다면 채팅 세션 목록을 반환하도록 수정해야 합니다.
    """
    return []


# API 라우터 포함 (버전 접두사 사용)
app.include_router(api_router, prefix=API_PREFIX)
app.include_router(root_router)

# 레거시 라우터 포함 (버전 접두사 없이 /api 경로에 매핑)
app.include_router(legacy_router, prefix="/api")


# Redirect /doc to /docs
@app.get("/doc", include_in_schema=False)
async def redirect_doc_to_docs() -> RedirectResponse: # Added return type
    return RedirectResponse(url="/docs")


# Custom Swagger UI
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse: # Added return type
    return get_swagger_ui_html(
        openapi_url=f"{API_PREFIX}/openapi.json",
        title=app.title,
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )


# Custom OpenAPI schema
def custom_openapi() -> Dict[str, Any]: # Added return type
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Customize the OpenAPI schema if needed
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi_schema = custom_openapi() # Changed to assign to openapi_schema attribute

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)