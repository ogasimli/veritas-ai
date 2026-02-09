# ==============================================================================
# Veritas AI - Project Makefile
# ==============================================================================

.PHONY: playground install dev test lint deploy deploy-backend deploy-frontend promote promote-backend promote-frontend teardown teardown-backend teardown-frontend extract-docx

#  Run Google ADK Web Playground
playground:
	$(MAKE) -C backend playground

# Install dependencies for both backend and frontend
install:
	@echo "Installing backend dependencies..."
	$(MAKE) -C backend install
	@echo "Installing frontend dependencies..."
	$(MAKE) -C frontend install

# Run both backend and frontend development servers
dev:
	@echo "Starting backend and frontend development servers..."
	@echo "Backend will be at http://localhost:8000"
	@echo "Frontend will be at http://localhost:3000"
	@npx -y concurrently --kill-others \
		"$(MAKE) -C backend dev" \
		"$(MAKE) -C frontend dev"

# Run tests for both components
test:
	@echo "Running backend tests..."
	$(MAKE) -C backend test
	@echo "Running frontend tests..."
	$(MAKE) -C frontend test

# Run linting for both components
lint:
	@echo "Linting backend..."
	$(MAKE) -C backend lint
	@echo "Linting frontend..."
	$(MAKE) -C frontend lint

# Pass env= only to deploy/teardown targets
# Example: make deploy env=staging
deploy deploy-backend deploy-frontend teardown teardown-backend teardown-frontend: export DEPLOY_ENV = $(env)

# Deploy the entire backend (including agents)
deploy-backend:
	@echo "Deploying backend..."
	$(MAKE) -C backend deploy

# Deploy frontend to Cloud Run
deploy-frontend:
	@echo "Deploying frontend..."
	$(MAKE) -C frontend deploy

# Deploy the entire project
# Usage: make deploy [env=staging]
deploy:
	$(MAKE) deploy-backend
	$(MAKE) deploy-frontend

# Promote staging images to production (no rebuild)
# Usage: make promote | make promote-backend | make promote-frontend
promote:
	./scripts/promote.sh

promote-backend:
	./scripts/promote.sh --backend-only

promote-frontend:
	./scripts/promote.sh --frontend-only

# Tear down Cloud Run services
# Usage: make teardown [env=staging]
teardown-backend:
	$(MAKE) -C backend teardown

teardown-frontend:
	$(MAKE) -C frontend teardown

teardown:
	$(MAKE) teardown-frontend
	$(MAKE) teardown-backend
