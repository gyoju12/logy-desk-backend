from fastapi import FastAPI, APIRouter
import uvicorn

# Initialize FastAPI app
app = FastAPI(title="Test Logy-Desk API")

# Create a simple router
router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


# Include the router
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("test_main:app", host="0.0.0.0", port=8000, reload=True)
