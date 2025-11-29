.PHONY: help install dev build start stop clean test lint docker-build docker-up docker-down

# Default target
help:
	@echo "{{PROJECT_TITLE}} - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install    Install all dependencies"
	@echo "  make dev        Start development servers"
	@echo "  make build      Build for production"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   Build Docker images"
	@echo "  make docker-up      Start services with Docker Compose"
	@echo "  make docker-down    Stop Docker services"
	@echo ""
	@echo "Utilities:"
	@echo "  make test       Run tests"
	@echo "  make lint       Run linters"
	@echo "  make clean      Clean build artifacts"

# Install all dependencies
install:
	@echo "Installing agent dependencies..."
	cd agent && pip install -e ".[dev]"
	@echo "Installing UI dependencies..."
	cd ui && npm install

# Start development servers
dev:
	@echo "Starting development servers..."
	@trap 'kill 0' INT; \
	(cd agent && python main.py) & \
	(cd ui && npm run dev) & \
	wait

# Build for production
build:
	@echo "Building UI..."
	cd ui && npm run build
	@echo "Build complete!"

# Start production servers
start:
	@echo "Starting production servers..."
	@trap 'kill 0' INT; \
	(cd agent && python main.py) & \
	(cd ui && npm start) & \
	wait

# Stop all servers
stop:
	@echo "Stopping servers..."
	-pkill -f "python main.py"
	-pkill -f "next"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf agent/__pycache__ agent/*.egg-info
	rm -rf ui/.next ui/node_modules

# Run tests
test:
	@echo "Running agent tests..."
	cd agent && pytest
	@echo "Running UI tests..."
	cd ui && npm test || true

# Run linters
lint:
	@echo "Linting agent..."
	cd agent && ruff check .
	@echo "Linting UI..."
	cd ui && npm run lint

# Docker commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down
