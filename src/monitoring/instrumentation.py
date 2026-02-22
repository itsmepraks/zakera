"""
Automatic Instrumentation Setup for FastAPI and Dependencies

This module handles automatic instrumentation of the FastAPI application
and its dependencies for distributed tracing.

Author: Prakriti Bista
Version: 1.0.0
"""

import logging
from typing import Optional

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from .tracing import setup_tracing, instrument_sqlalchemy_engine

logger = logging.getLogger(__name__)


def instrument_app(
    app: FastAPI,
    service_name: str = "zakera-api",
    service_version: str = "0.6.0",
    environment: str = "development",
) -> None:
    """
    Instrument FastAPI application with OpenTelemetry.
    
    This function should be called during application startup to enable
    automatic tracing of all HTTP requests.
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service
        service_version: Version of the service
        environment: Deployment environment
    
    Usage:
        from fastapi import FastAPI
        from monitoring.instrumentation import instrument_app
        
        app = FastAPI()
        
        @app.on_event("startup")
        async def startup():
            instrument_app(app)
    """
    try:
        # Initialize tracing
        setup_tracing(
            service_name=service_name,
            service_version=service_version,
            environment=environment,
        )
        
        # Instrument FastAPI app
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="/health,/metrics,/favicon.ico",  # Don't trace health checks
            tracer_provider=None,  # Use default
        )
        
        logger.info(f"FastAPI application instrumented: {service_name}")
        
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI application: {e}", exc_info=True)


def instrument_database(engine) -> None:
    """
    Instrument SQLAlchemy database engine.
    
    Args:
        engine: SQLAlchemy engine instance
    
    Usage:
        from sqlalchemy import create_engine
        from monitoring.instrumentation import instrument_database
        
        engine = create_engine(DATABASE_URL)
        instrument_database(engine)
    """
    try:
        instrument_sqlalchemy_engine(engine)
        logger.info("Database engine instrumented for tracing")
    except Exception as e:
        logger.error(f"Failed to instrument database: {e}", exc_info=True)
