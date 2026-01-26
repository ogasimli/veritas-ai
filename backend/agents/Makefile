
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
# Backend Deployment Targets
# ==============================================================================

# Deploy all agents (root + sub-agents) to Cloud Run
deploy-all: deploy-root-agent deploy-numeric-agent deploy-logic-agent deploy-disclosure-agent deploy-external-agent
	@echo "✅ All agents deployed successfully!"
	@echo ""
	@echo "Deployed services:"
	@echo "  - veritas-ai-agent (root orchestrator)"
	@echo "  - veritas-numeric-validation"
	@echo "  - veritas-logic-consistency"
	@echo "  - veritas-disclosure-compliance"
	@echo "  - veritas-external-signal"

# Common deployment variables
PROJECT_ID = $(shell gcloud config get-value project)
REGION = us-central1
ENV_VARS = $(shell grep -v '^\#' .env | xargs | sed 's/ /,/g')

# Helper macro for deploying agents to Cloud Run
define deploy_agent
	uv run adk deploy cloud_run \
		--project=$(PROJECT_ID) \
		--region=$(REGION) \
		--service_name="$(1)" \
		--with_ui \
		"./veritas_ai_agent" \
		-- --allow-unauthenticated \
		--timeout=3600 \
		--set-env-vars $(ENV_VARS),VERITAS_AGENT_MODE=$(2)
endef

# Deploy root orchestrator agent
deploy-root-agent:
	$(call deploy_agent,veritas-orchestrator-agent,orchestrator)

# Deploy numeric validation sub-agent
deploy-numeric-agent:
	$(call deploy_agent,veritas-numeric-validation,numeric_validation)

# Deploy logic consistency sub-agent
deploy-logic-agent:
	$(call deploy_agent,veritas-logic-consistency,logic_consistency)

# Deploy disclosure compliance sub-agent
deploy-disclosure-agent:
	$(call deploy_agent,veritas-disclosure-compliance,disclosure_compliance)

# Deploy external signal sub-agent
deploy-external-agent:
	$(call deploy_agent,veritas-external-signal,external_signal)

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