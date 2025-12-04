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
# Note: uv installs to /root/.local/bin by default now
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:/root/.cargo/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files and README (required by pyproject.toml)
COPY pyproject.toml uv.lock README.md ./

# Copy source code first (needed for package installation)
COPY src/ ./src/

# Install dependencies and the package
# Using explicit path in case ENV doesn't take effect in same layer
RUN /root/.local/bin/uv sync --all-extras

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

# Create directories for data persistence
RUN mkdir -p /app/data /app/downloads /app/plugins && \
    chown -R odin:odin /app

# Switch to non-root user
USER odin

# Expose single unified port
# All protocols available via path routing:
#   /a2a/*        - A2A protocol
#   /mcp/*        - MCP Streamable HTTP
#   /agui/*       - AG-UI protocol
#   /copilotkit/* - CopilotKit protocol
#   /api/*        - REST API
#   /health       - Health check
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: start the unified Odin server
CMD ["python", "-m", "odin", "serve", "--unified", "--host", "0.0.0.0", "--port", "8000"]
