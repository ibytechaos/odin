#!/bin/bash
# Odin Demo Startup Script
# Usage: ./start.sh [backend|frontend|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default values
HOST=${HOST:-0.0.0.0}
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-3000}
PROTOCOL=${PROTOCOL:-copilotkit}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi

    # Check Node.js for frontend
    if ! command -v node &> /dev/null; then
        log_warn "Node.js is not installed (required for frontend)"
    fi

    # Check uv
    if ! command -v uv &> /dev/null; then
        log_warn "uv is not installed, using pip instead"
    fi
}

start_backend() {
    log_info "Starting backend server..."
    log_info "Protocol: $PROTOCOL"
    log_info "URL: http://$HOST:$BACKEND_PORT"

    cd "$SCRIPT_DIR"

    # Use PYTHONPATH to include src directory
    export PYTHONPATH="$SCRIPT_DIR/../../src:$PYTHONPATH"

    python3 main.py --protocol "$PROTOCOL" --host "$HOST" --port "$BACKEND_PORT"
}

start_frontend() {
    log_info "Starting frontend server..."
    log_info "URL: http://localhost:$FRONTEND_PORT"

    cd "$SCRIPT_DIR/frontend"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        log_info "Installing frontend dependencies..."
        npm install
    fi

    # Set port via environment variable
    PORT=$FRONTEND_PORT npm run dev
}

start_all() {
    log_info "Starting both backend and frontend..."

    # Start backend in background
    start_backend &
    BACKEND_PID=$!

    # Wait a bit for backend to start
    sleep 2

    # Start frontend in background
    start_frontend &
    FRONTEND_PID=$!

    log_info "Backend PID: $BACKEND_PID"
    log_info "Frontend PID: $FRONTEND_PID"
    log_info ""
    log_info "Services running:"
    log_info "  Backend:  http://localhost:$BACKEND_PORT"
    log_info "  Frontend: http://localhost:$FRONTEND_PORT"
    log_info ""
    log_info "Press Ctrl+C to stop all services"

    # Handle Ctrl+C
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

    # Wait for both processes
    wait
}

show_help() {
    echo "Odin Demo Startup Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  backend   Start backend server only"
    echo "  frontend  Start frontend server only"
    echo "  all       Start both backend and frontend (default)"
    echo "  help      Show this help message"
    echo ""
    echo "Environment variables (set in .env):"
    echo "  HOST           Backend host (default: 0.0.0.0)"
    echo "  BACKEND_PORT   Backend port (default: 8000)"
    echo "  FRONTEND_PORT  Frontend port (default: 3000)"
    echo "  PROTOCOL       Protocol: copilotkit|agui|a2a (default: copilotkit)"
    echo ""
    echo "Examples:"
    echo "  $0              # Start both servers"
    echo "  $0 backend      # Start backend only"
    echo "  $0 frontend     # Start frontend only"
}

# Main
check_dependencies

case "${1:-all}" in
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    all)
        start_all
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
