FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Install dependencies
# Copy pyproject.toml files and lock files for both backend and agents
COPY pyproject.toml uv.lock ./
COPY agents/pyproject.toml ./agents/
COPY agents/uv.lock ./agents/

# Copy the full agents directory (needed as a path dependency)
COPY agents/ ./agents/

# Install dependencies using uv
# --system installs into the system python, avoiding the need for activation
RUN uv pip install --system . 

# Copy application code
COPY app/ ./app/
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Expose port
EXPOSE 8080

# Run the application
# Cloud Run expects 0.0.0.0 and defaults to port 8080
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8080"]
