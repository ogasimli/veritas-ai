.PHONY: install playground deploy-all deploy-root-agent deploy-numeric-agent deploy-numeric-cross-table deploy-numeric-in-table deploy-numeric-all deploy-logic-agent deploy-disclosure-agent deploy-external-agent backend test lint

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
	@echo "  - veritas-numeric-validation (In-Table & Legacy Cross-Check)"
	@echo "  - veritas-numeric-validation-legacy (Legacy Only)"
	@echo "  - veritas-numeric-validation-table (In-Table Only)"
	@echo "  - veritas-logic-consistency"
	@echo "  - veritas-disclosure-compliance"
	@echo "  - veritas-external-signal"

# Common deployment variables
PROJECT_ID = $(shell gcloud config get-value project)
REGION = us-central1
# Get env vars from .env, commenting out and excluding the ones we set explicitly
ENV_VARS = $(shell grep -vE '^(VERITAS_AGENT_MODE|NUMERIC_VALIDATION_AGENT_MODE)=' .env | grep -v '^\#' | xargs | sed 's/ /,/g')

# Helper macro for deploying agents to Cloud Run
define deploy_agent
	@echo "📦 Generating requirements.txt for ADK deployment..."
	uv pip compile pyproject.toml --output-file veritas_ai_agent/requirements.txt
	uv run adk deploy cloud_run \
		--project=$(PROJECT_ID) \
		--region=$(REGION) \
		--service_name="$(1)" \
		--with_ui \
		"./veritas_ai_agent" \
		-- --allow-unauthenticated \
		--timeout=3600 \
		--set-env-vars $(ENV_VARS),VERITAS_AGENT_MODE=$(2),NUMERIC_VALIDATION_AGENT_MODE=$(if $(3),$(3),all)
endef

# Deploy root orchestrator agent
deploy-root-agent:
	$(call deploy_agent,veritas-orchestrator-agent,orchestrator)

# Deploy numeric validation sub-agents (3 versions)
deploy-numeric-agent: deploy-numeric-cross-table deploy-numeric-in-table deploy-numeric-all

deploy-numeric-cross-table:
	$(call deploy_agent,veritas-numeric-validation-cross-table,numeric_validation,cross_table_pipeline)

deploy-numeric-in-table:
	$(call deploy_agent,veritas-numeric-validation-table,numeric_validation,in_table_pipeline)

deploy-numeric-all:
	$(call deploy_agent,veritas-numeric-validation,numeric_validation,all)

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
	uv run pytest tests/unit

# Run code quality checks (codespell, ruff, ty)
lint:
	uv sync --dev --extra lint
	uv run codespell
	uv run ruff check . --fix
	uv run ruff format .
	uv run ty check .