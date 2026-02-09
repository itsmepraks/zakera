from fastapi import APIRouter
from datetime import datetime
import sys

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "python_version": sys.version,
        "service": "zakera-api"
    }

@router.get("/status")
async def status():
    """Detailed status information"""
    return {
        "api_version": "0.1.0",
        "status": "operational",
        "uptime": "N/A",  # TODO: Implement uptime tracking
        "features": {
            "chat": True,
            "memory": True,
            "tools": True,
            "streaming": True
        }
    }
