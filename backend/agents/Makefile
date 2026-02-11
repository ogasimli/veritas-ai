.PHONY: install playground deploy-agent deploy-all backend test lint

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

# Common deployment variables
PROJECT_ID = $(shell gcloud config get-value project)
REGION = us-central1
# Get env vars from .env, commenting out and excluding the ones we set explicitly
ENV_VARS = $(shell grep -vE '^(VERITAS_AGENT_MODE|NUMERIC_VALIDATION_AGENT_MODE)=' .env | grep -v '^\#' | xargs | sed 's/ /,/g')

# Helper macro for deploying agents to Cloud Run
define _deploy_agent_internal
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

# Deploy agents
# Usage: make deploy-agent agent=<agent_name> [variant=<variant>]
#   make deploy-agent agent=orchestrator
#   make deploy-agent agent=numeric variant=cross_table
#   make deploy-agent agent=numeric variant=in_table
#   make deploy-agent agent=numeric variant=all
#   make deploy-agent agent=logic
#   make deploy-agent agent=disclosure
#   make deploy-agent agent=external
deploy-agent:
ifndef agent
	$(error agent is required. Usage: make deploy-agent agent=orchestrator|numeric|logic|disclosure|external [variant=cross_table|in_table|all])
endif
ifeq ($(agent),orchestrator)
	$(call _deploy_agent_internal,veritas-orchestrator-agent,orchestrator)
else ifeq ($(agent),numeric)
ifndef variant
	$(error variant is required for numeric agent. Usage: make deploy-agent agent=numeric variant=cross_table|in_table|all)
endif
ifeq ($(variant),cross_table)
	$(call _deploy_agent_internal,veritas-numeric-validation-cross-table,numeric_validation,cross_table_pipeline)
else ifeq ($(variant),in_table)
	$(call _deploy_agent_internal,veritas-numeric-validation-table,numeric_validation,in_table_pipeline)
else ifeq ($(variant),all)
	$(call _deploy_agent_internal,veritas-numeric-validation,numeric_validation,all)
else
	$(error Invalid variant for numeric agent. Use: cross_table, in_table, or all)
endif
else ifeq ($(agent),logic)
	$(call _deploy_agent_internal,veritas-logic-consistency,logic_consistency)
else ifeq ($(agent),disclosure)
	$(call _deploy_agent_internal,veritas-disclosure-compliance,disclosure_compliance)
else ifeq ($(agent),external)
	$(call _deploy_agent_internal,veritas-external-signal,external_signal)
else
	$(error Invalid agent. Use: orchestrator, numeric, logic, disclosure, or external)
endif

# Deploy all agents (root + sub-agents) to Cloud Run
deploy-all:
	$(MAKE) deploy-agent agent=orchestrator
	$(MAKE) deploy-agent agent=numeric variant=cross_table
	$(MAKE) deploy-agent agent=numeric variant=in_table
	$(MAKE) deploy-agent agent=numeric variant=all
	$(MAKE) deploy-agent agent=logic
	$(MAKE) deploy-agent agent=disclosure
	$(MAKE) deploy-agent agent=external
	@echo "✅ All agents deployed successfully!"
	@echo ""
	@echo "Deployed services:"
	@echo "  - veritas-orchestrator-agent (root orchestrator)"
	@echo "  - veritas-numeric-validation (In-Table & Legacy Cross-Check)"
	@echo "  - veritas-numeric-validation-cross-table (Legacy Only)"
	@echo "  - veritas-numeric-validation-table (In-Table Only)"
	@echo "  - veritas-logic-consistency"
	@echo "  - veritas-disclosure-compliance"
	@echo "  - veritas-external-signal"

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