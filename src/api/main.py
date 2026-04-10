from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
from contextlib import asynccontextmanager
import uuid
import os
import time

from .routes import chat, conversations, health, auth, tools, analytics, search, models, monitoring, feedback, benchmark
from .config import settings
from .database import init_db, SessionLocal

# Import monitoring components
from src.monitoring.metrics import metrics_middleware, system_metrics_collector
from src.monitoring.logging import setup_logging, get_logger
from src.monitoring.health import health_checker, check_database_health, check_system_resources, check_model_providers
from src.monitoring.alerts import register_default_alerts

# Setup logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE", "logs/zakera.log"),
    json_logs=os.getenv("JSON_LOGS", "true").lower() == "true",
    enable_rotation=True,
    max_file_size="10 MB",
    retention="7 days"
)

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Zakera AI Chat Agent...")
    
    logger.info("📦 Initializing database...")
    init_db()
    logger.info("✅ Database initialized")
    
    logger.info("🔐 Authentication system ready")
    logger.info("🤖 Model providers configured")
    logger.info("🛠️  Tool system loaded")
    
    # Register health checks
    logger.info("💊 Registering health checks...")
    
    # Initialize a session for the database health check
    db_session = SessionLocal()
    health_checker.register_check("database", lambda: check_database_health(db_session))
    
    health_checker.register_check("system_resources", check_system_resources, critical=False)
    health_checker.register_check("model_providers", check_model_providers, critical=False)
    
    # Register vector memory health check
    from src.model.memory_vector import SENTENCE_TRANSFORMERS_AVAILABLE, FAISS_AVAILABLE
    async def check_vector_memory():
        return {
            "sentence_transformers": SENTENCE_TRANSFORMERS_AVAILABLE,
            "faiss": FAISS_AVAILABLE,
            "status": "healthy" if SENTENCE_TRANSFORMERS_AVAILABLE else "unhealthy"
        }
    health_checker.register_check("vector_memory", check_vector_memory, critical=False)
    
    logger.info("✅ Health checks registered")
    
    # Start system metrics collection
    logger.info("📊 Starting metrics collection...")
    await system_metrics_collector.start()
    logger.info("✅ Metrics collection started")
    
    # Register default alerts
    logger.info("🚨 Registering alert rules...")
    register_default_alerts()
    logger.info("✅ Alert rules registered")
    
    logger.info("🎉 Zakera is ready to serve requests!")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Zakera...")
    await system_metrics_collector.stop()
    db_session.close()
    logger.info("✅ Shutdown complete")

app = FastAPI(
    title="Zakera AI Chat Agent",
    description="Intelligent chat agent with conversation memory, multi-provider LLM support, tool integration, and comprehensive monitoring",
    version="0.7.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Add metrics middleware
metrics_middleware(app)

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Log request
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else None
    )
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response

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
app.include_router(monitoring.router, prefix="/api/v1", tags=["monitoring"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(models.router, prefix="/api/v1", tags=["models"])
app.include_router(conversations.router, prefix="/api/v1", tags=["conversations"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(tools.router, prefix="/api/v1", tags=["tools"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])
app.include_router(benchmark.router, prefix="/v1")

@app.get("/")
async def root():
    return {
        "message": "Zakera AI Chat Agent API",
        "version": "0.7.0",
        "status": "operational",
        "features": {
            "database": "✅ SQLAlchemy with persistent storage",
            "authentication": "✅ JWT-based user authentication",
            "conversations": "✅ Full CRUD with user isolation",
            "messages": "✅ Persistent message history",
            "websockets": "✅ Real-time streaming with auth",
            "models": "✅ Multi-provider LLM support (OpenAI, Anthropic, Gemini, Ollama, HuggingFace)",
            "local_models": "✅ Local model support via Ollama and HuggingFace",
            "model_fallback": "✅ Intelligent fallback strategies",
            "tools": "✅ Extensible tool system",
            "analytics": "✅ Usage analytics and monitoring",
            "search": "✅ Conversation search",
            "monitoring": "✅ Prometheus metrics, health checks, alerts",
            "observability": "✅ Structured logging, performance tracking",
            "feedback": "✅ User message feedback system"
        },
        "providers": {
            "api_based": ["OpenAI", "Anthropic", "Google Gemini", "Groq"],
            "local": ["Ollama", "HuggingFace Transformers"]
        },
        "monitoring": {
            "metrics": "/api/v1/monitoring/metrics",
            "health": "/api/v1/monitoring/health",
            "alerts": "/api/v1/monitoring/alerts",
            "performance": "/api/v1/monitoring/performance",
            "prometheus": "http://localhost:9090",
            "grafana": "http://localhost:3001"
        },
        "docs": "/api/docs",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        request_id=request_id,
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": str(type(exc).__name__),
            "request_id": request_id
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_config=None  # Use our custom logging
    )
