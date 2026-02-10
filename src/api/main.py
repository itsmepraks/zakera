from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
from contextlib import asynccontextmanager

from .routes import chat, conversations, health
from .config import settings
from .database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    print("🚀 Starting Zakera AI Chat Agent...")
    print("📦 Initializing database...")
    init_db()
    print("✅ Database initialized")
    yield
    # Shutdown
    print("👋 Shutting down Zakera...")

app = FastAPI(
    title="Zakera AI Chat Agent",
    description="Intelligent chat agent with conversation memory and tool integration",
    version="0.2.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(conversations.router, prefix="/api/v1", tags=["conversations"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])

@app.get("/")
async def root():
    return {
        "message": "Zakera AI Chat Agent API",
        "version": "0.2.0",
        "features": {
            "database": "✅ SQLAlchemy with persistent storage",
            "conversations": "✅ Full CRUD operations",
            "messages": "✅ Persistent message history",
            "authentication": "🚧 Coming soon"
        },
        "docs": "/api/docs",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": str(type(exc).__name__)}
    )

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
