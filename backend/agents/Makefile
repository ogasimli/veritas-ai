
# ==============================================================================
# Installation & Setup
# ==============================================================================

# Install dependencies using uv package manager
install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.8.13/install.sh | sh; source $HOME/.local/bin/env; }
	uv sync

# ==============================================================================
# Playground Targets
# ==============================================================================

# Launch local dev playground
playground:
	@echo "=================================================================================="
	@echo "| 🚀 Starting your agent playground...                                           |"
	@echo "|                                                                                |"
	@echo "| 💡 Try asking: What's the weather in San Francisco?                            |"
	@echo "|                                                                                |"
	@echo "| 🔍 IMPORTANT: Select the 'veritas_ai_agent' folder to interact with your agent.|"
	@echo "=================================================================================="
	uv run adk web . --port 8501 --reload_agents

# ==============================================================================
# Local Development Commands
# ==============================================================================

# Launch local development server with hot-reload
local-backend:
	uv run uvicorn veritas_ai_agent.fast_api_app:app --host localhost --port 8000 --reload

# ==============================================================================
# Backend Deployment Targets
# ==============================================================================

# Deploy the agent remotely
deploy:
	PROJECT_ID=$$(gcloud config get-value project) && \
	ENV_VARS=$$(grep -v '^#' .env | xargs | sed 's/ /,/g') && \
	adk deploy cloud_run \
		--project=$$PROJECT_ID \
		--region="us-central1" \
		--service_name="veritas-ai-agent" \
		--with_ui \
		"./veritas_ai_agent" \
		-- --allow-unauthenticated \
		--set-env-vars $$ENV_VARS

# Alias for 'make deploy' for backward compatibility
backend: deploy

# ==============================================================================
# Testing & Code Quality
# ==============================================================================

# Run unit and integration tests
test:
	uv sync --dev
	uv run pytest tests/unit && uv run pytest tests/integration

# Run code quality checks (codespell, ruff, ty)
lint:
	uv sync --dev --extra lint
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run ty check .