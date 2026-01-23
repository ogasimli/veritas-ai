# ==============================================================================
# Installation & Setup
# ==============================================================================

# Install dependencies using uv package manager
install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.8.13/install.sh | sh; source $$HOME/.local/bin/env; }
	uv sync

# ==============================================================================
# Development Commands
# ==============================================================================

# Launch FastAPI development server with hot-reload
dev:
	uv run uvicorn app.main:app --host localhost --port 8000 --reload

# ==============================================================================
# Testing & Code Quality
# ==============================================================================

# Run unit and integration tests
test:
	uv run pytest tests/

# Run code quality checks (ruff and codespell)
lint:
	uv run codespell
	uv run ruff check .
	uv run ruff format . --check

# ==============================================================================
# Deployment
# ==============================================================================

# Deploy to Cloud Run (integration with agents/Makefile flow)
deploy:
	$(MAKE) -C agents deploy
