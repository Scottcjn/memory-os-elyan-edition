FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (build-essential for fastembed, python3-dev for C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -r -u 10001 appuser

# Copy source code with correct ownership
COPY --chown=appuser:appuser . .

# Default environment variables (override via docker-compose)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import redis; r=redis.from_url('redis://redis:6379'); r.ping()" || exit 1

CMD ["python", "main.py", "--run-worker"]
