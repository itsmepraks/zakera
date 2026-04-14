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
from src.monitoring.tracing import setup_tracing, instrument_fastapi

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
    logger.info("Starting Zakera AI Chat Agent")

    init_db()
    logger.info("Database initialized")

    # Register health checks
    db_session = SessionLocal()
    health_checker.register_check("database", lambda: check_database_health(db_session))
    health_checker.register_check("system_resources", check_system_resources, critical=False)
    health_checker.register_check("model_providers", check_model_providers, critical=False)
    logger.info("Health checks registered")

    # Start system metrics collection
    await system_metrics_collector.start()
    logger.info("Metrics collection started")

    # Register default alerts
    register_default_alerts()
    logger.info("Alert rules registered")

    # Initialize distributed tracing
    environment = os.getenv("ENVIRONMENT", "development")
    setup_tracing(
        service_name="zakera",
        service_version="0.7.0",
        environment=environment,
    )
    instrument_fastapi(app)
    logger.info("Tracing initialized (env=%s)", environment)

    logger.info("Zakera is ready to serve requests")

    yield

    # Shutdown
    logger.info("Shutting down Zakera")
    await system_metrics_collector.stop()
    db_session.close()
    logger.info("Shutdown complete")

app = FastAPI(
    title="Zakera AI Chat Agent",
    description="AI agent orchestrator with multi-provider LLM support, conversation memory, and tool integration",
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
        "message": "Zakera API",
        "version": "0.7.0",
        "status": "operational",
        "docs": "/api/docs",
        "health": "/api/v1/monitoring/health",
        "metrics": "/api/v1/monitoring/metrics",
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
