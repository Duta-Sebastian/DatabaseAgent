# Multi-stage build with uv
FROM python:3.13-slim AS base

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy dependency definitions
COPY pyproject.toml uv.lock* ./

# Install dependencies (creates /app/.venv automatically)
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.13-slim AS production

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy the virtual environment from base stage
COPY --from=base /app/.venv /app/.venv

# Ensure uv's venv is used
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 agentuser && \
    chown -R agentuser:agentuser /app

# Environment variables with defaults (REMOVED HARDCODED API KEY)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POSTGRES_HOST=postgres \
    POSTGRES_PORT=5432 \
    POSTGRES_DB=agent_db \
    POSTGRES_USER=postgres \
    POSTGRES_PASSWORD=password

# Switch to non-root user
USER agentuser

# Health check that works with non-interactive environment
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from database.connection import engine; engine.connect().close()" || exit 1

# Expose port for potential web interface
EXPOSE 8000

# Setup database and drop to bash
CMD ["sh", "-c", "while ! pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -q; do echo 'Waiting for PostgreSQL...'; sleep 2; done && echo 'PostgreSQL ready' && python -m alembic upgrade head && python -m database.seed && echo 'Database setup complete. Dropping to bash...' && exec /bin/bash"]