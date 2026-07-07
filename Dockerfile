# ==============================================================================
# Multi-stage DevOps Dockerfile
# ==============================================================================
# This Dockerfile utilizes multi-stage builds to optimize image sizes and cache
# identical compilation layers (like python packages) across all three pipeline
# containers (ETL, API, Dashboard).
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Base Runtime Environment
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and buffer output streams for logging
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system libraries required to build python extensions and run healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements for installation
COPY requirements-backend.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire workspace into the base container
COPY . .


# ------------------------------------------------------------------------------
# Stage 2: ETL Stream Ingestion Service
# ------------------------------------------------------------------------------
FROM base AS etl
# Runs the streaming ETL daemon as default
CMD ["python", "extract/stream_generator.py"]


# ------------------------------------------------------------------------------
# Stage 3: FastAPI Backend REST & WebSocket Service
# ------------------------------------------------------------------------------
FROM base AS api
EXPOSE 8000
# Runs the FastAPI server via Uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]


# ------------------------------------------------------------------------------
# Stage 4: Streamlit Frontend Dashboard Service
# ------------------------------------------------------------------------------
FROM base AS dashboard
EXPOSE 8501
# Runs Streamlit and binds to all interfaces
CMD ["streamlit", "run", "dashboard/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
