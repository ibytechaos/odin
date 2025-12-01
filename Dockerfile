# Odin Framework Dockerfile
# Multi-stage build for optimized production image

# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.14-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (with builtin-plugins extras for browser automation)
RUN uv sync --frozen --no-dev --extra builtin-plugins

# Copy source code
COPY src/ ./src/

# Install the package
RUN uv pip install --no-deps -e .

# Note: Playwright browsers are NOT installed in the container
# We use remote Chrome debugging via CHROME_DEBUG_HOST instead
# If you need local browser, uncomment:
# RUN uv run playwright install chromium

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.14-slim AS runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # For playwright/browser automation
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    # For pdf2image
    poppler-utils \
    # Common utilities
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 odin
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Set environment variables
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default Odin configuration
ENV ODIN_ENV=production
ENV ODIN_LOG_LEVEL=INFO
ENV HTTP_HOST=0.0.0.0
ENV HTTP_PORT=8000

# Create directories for data persistence
RUN mkdir -p /app/data /app/downloads /app/plugins && \
    chown -R odin:odin /app

# Switch to non-root user
USER odin

# Expose ports
# HTTP/REST API
EXPOSE 8000
# MCP Server
EXPOSE 8001
# A2A Protocol
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${HTTP_PORT}/health || exit 1

# Default command: start the Odin server with CopilotKit protocol
CMD ["python", "-m", "odin", "serve", "--protocol", "copilotkit", "--host", "0.0.0.0", "--port", "8000"]
