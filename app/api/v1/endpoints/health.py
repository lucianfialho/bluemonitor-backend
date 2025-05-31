"""Health check endpoints."""
from fastapi import APIRouter, Depends
from starlette import status

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """Basic health check endpoint.
    
    Returns:
        dict: Status message indicating the service is running.
    """
    return {"status": "ok"}
