.PHONY: install dev test lint deploy teardown

# ==============================================================================
# Installation & Setup
# ==============================================================================

# Install dependencies
install:
	npm install

# ==============================================================================
# Development Commands
# ==============================================================================

# Launch Next.js development server with hot-reload
dev:
	npm run dev

# ==============================================================================
# Testing & Code Quality
# ==============================================================================

# Run tests
test:
	npm test --if-present

# Run linting
lint:
	npm run lint --if-present

# ==============================================================================
# Deployment
# ==============================================================================

# Deploy to Cloud Run
deploy:
	./scripts/deploy.sh

# Tear down Cloud Run service
teardown:
	./scripts/teardown.sh
