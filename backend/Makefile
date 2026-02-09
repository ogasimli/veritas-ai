.PHONY: install dev db-stop migrate extract-docx test lint deploy teardown playground

# ==============================================================================
# Installation & Setup
# ==============================================================================

# Install dependencies using uv package manager
install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.8.13/install.sh | sh; source $$HOME/.local/bin/env; }
	uv sync --all-extras

# ==============================================================================
# Development Commands
# ==============================================================================

# Launch FastAPI development server with hot-reload (starts local DB automatically)
dev:
	docker compose up -d db
	uv run alembic upgrade head
	uv run uvicorn app.main:app --host localhost --port 8000 --reload

# Stop local database
db-stop:
	docker compose down

# Create a new migration
# Usage: make migrate msg="migration message"
migrate:
ifndef msg
	$(error msg is required. Usage: make migrate msg="migration message")
endif
	uv run alembic revision --autogenerate -m "$(msg)"

# Extract markdown from a .docx file
# Usage: make extract-docx file=/absolute/path/to/document.docx
extract-docx:
ifndef file
	$(error file is required. Usage: make extract-docx file=/absolute/path/to/document.docx)
endif
	uv run python scripts/docx_extraction.py "$(file)"

# ==============================================================================
# Testing & Code Quality
# ==============================================================================

# Run unit and integration tests
test:
	uv run pytest tests/
	$(MAKE) -C agents test

# Run code quality checks (ruff and codespell)
lint:
	uv run codespell
	uv run ruff check . --fix
	uv run ruff format .
	$(MAKE) -C agents lint

# ==============================================================================
# Deployment
# ==============================================================================

# Deploy to Cloud Run (integration with agents/Makefile flow + Backend API)
deploy:
	./scripts/deploy.sh

# Tear down Cloud Run service
teardown:
	./scripts/teardown.sh

# ==============================================================================
# Run Google ADK Web Playground
# ==============================================================================

playground:
	$(MAKE) -C agents playground
