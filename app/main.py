import os
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse
from fastapi.routing import APIRouter

# Import API routers
from app.api.router import api_router

# API version
API_PREFIX = "/api/v1"


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
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
root_router = APIRouter(prefix=API_PREFIX)


# Health check endpoint
@root_router.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy"}


# Include API routers with version prefix
app.include_router(api_router, prefix=API_PREFIX)
app.include_router(root_router)


# Redirect /doc to /docs
@app.get("/doc", include_in_schema=False)
async def redirect_doc_to_docs():
    return RedirectResponse(url="/docs")


# Custom Swagger UI
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=f"{API_PREFIX}/openapi.json",
        title=app.title,
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )


# Custom OpenAPI schema
def custom_openapi():
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


app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)
