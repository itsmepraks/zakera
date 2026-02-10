# Multi-stage Dockerfile for Zakera AI Chat Agent
# Stage 1: Backend Builder
FROM python:3.11-slim as backend-builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production Backend
FROM python:3.11-slim as backend

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 zakera && \
    mkdir -p /app/data && \
    chown -R zakera:zakera /app

# Copy Python dependencies from builder
COPY --from=backend-builder /root/.local /home/zakera/.local

# Copy application code
COPY --chown=zakera:zakera src/ ./src/
COPY --chown=zakera:zakera config/ ./config/
COPY --chown=zakera:zakera scripts/ ./scripts/

# Set environment variables
ENV PATH=/home/zakera/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

USER zakera

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
