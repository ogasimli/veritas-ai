# ==============================================================================
# Veritas AI - Project Makefile
# ==============================================================================

.PHONY: playground install dev test lint deploy promote teardown extract-docx

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
deploy teardown: export DEPLOY_ENV = $(env)

# Deploy services
# Usage: make deploy [service=backend|frontend] [env=staging]
#   make deploy              - Deploy both backend and frontend
#   make deploy service=backend
#   make deploy service=frontend
deploy:
ifeq ($(service),backend)
	@echo "Deploying backend..."
	$(MAKE) -C backend deploy
else ifeq ($(service),frontend)
	@echo "Deploying frontend..."
	$(MAKE) -C frontend deploy
else
	@echo "Deploying backend..."
	$(MAKE) -C backend deploy
	@echo "Deploying frontend..."
	$(MAKE) -C frontend deploy
endif

# Promote staging images to production (no rebuild)
# Usage: make promote [service=backend|frontend]
#   make promote              - Promote both backend and frontend
#   make promote service=backend
#   make promote service=frontend
promote:
ifeq ($(service),backend)
	./scripts/promote.sh --backend-only
else ifeq ($(service),frontend)
	./scripts/promote.sh --frontend-only
else
	./scripts/promote.sh
endif

# Tear down Cloud Run services
# Usage: make teardown [service=backend|frontend] [env=staging]
#   make teardown              - Tear down both backend and frontend
#   make teardown service=backend
#   make teardown service=frontend
teardown:
ifeq ($(service),backend)
	$(MAKE) -C backend teardown
else ifeq ($(service),frontend)
	$(MAKE) -C frontend teardown
else
	$(MAKE) -C frontend teardown
	$(MAKE) -C backend teardown
endif
