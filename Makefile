# ==============================================================================
# Veritas AI - Project Makefile
# ==============================================================================

.PHONY: install dev test lint deploy

# Install dependencies for both backend and frontend
install:
	@echo "Installing backend dependencies..."
	$(MAKE) -C backend install
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# Run both backend and frontend development servers
dev:
	@echo "Starting backend and frontend development servers..."
	@echo "Backend will be at http://localhost:8000"
	@echo "Frontend will be at http://localhost:3000"
	@npx -y concurrently --kill-others \
		"$(MAKE) -C backend dev" \
		"cd frontend && npm run dev"

# Run tests for both components
test:
	@echo "Running backend tests..."
	$(MAKE) -C backend test
	@echo "Running frontend tests..."
	cd frontend && npm test --if-present

# Run linting for both components
lint:
	@echo "Linting backend..."
	$(MAKE) -C backend lint
	@echo "Linting frontend..."
	cd frontend && npm run lint --if-present

# Deploy the entire backend (including agents)
deploy:
	@echo "Deploying backend..."
	$(MAKE) -C backend deploy
