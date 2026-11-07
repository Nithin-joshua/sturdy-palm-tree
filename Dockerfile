# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install curl for container health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install lightweight dependencies
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# Copy application assets and code
COPY backend /app/backend
COPY frontend /app/frontend
COPY data /app/data
COPY .env.example /app/.env.example

# Create writable output directory and configure non-root user
RUN mkdir -p /app/outputs && \
    useradd -u 1000 -m appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Health check verifying API availability
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Launch unified server supporting dynamic cloud PORT injection
CMD ["sh", "-c", "uvicorn backend.app.main:app --host ${HOST} --port ${PORT}"]
