from fastapi import APIRouter
from . import endpoints

# Create auth router
router = APIRouter(prefix="", tags=["Authentication"])

# Include all auth endpoints directly
router.include_router(endpoints.router)
