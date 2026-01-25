FROM python:3.10-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Install dependencies
# Copy pyproject.toml and agents directory first (since agents is a dependency)
COPY pyproject.toml .
# We need to copy the agents directory because it's a path dependency in pyproject.toml
COPY agents/ ./agents/

# Install dependencies using uv
# --system installs into the system python, avoiding the need for activation
RUN uv pip install --system . 

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8080

# Run the application
# Cloud Run expects 0.0.0.0 and defaults to port 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
