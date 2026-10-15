# ==============================================================================
# HAMSA OSINT ENTERPRISE BACKEND DOCKERFILE
# Base OS: Debian 12 (Bookworm Slim) - Full compatibility with Debian & Ubuntu
# ==============================================================================

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8888

# Install system dependencies for PostgreSQL libpq and health monitoring
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application source code
COPY . .

# CRITICAL SECURITY RULE: Expose port 8888 (never touch port 8080)
EXPOSE 8888

# Healthcheck probe
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8888/api/health || exit 1

# Launch Enterprise ASGI server with Uvicorn
CMD ["uvicorn", "hamsa.web.enterprise_app:app", "--host", "0.0.0.0", "--port", "8888", "--workers", "2"]
