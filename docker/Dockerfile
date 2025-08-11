# Multi-stage Docker build for the MCP server using UV
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv-cache

# Create non-root user
RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser

# Set working directory
WORKDIR /app

# Install system dependencies and UV
RUN apt-get update && apt-get install -y \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# Add UV to path
ENV PATH="/root/.cargo/bin:$PATH"

# Copy dependency files first for better caching
COPY pyproject.toml .
COPY requirements.txt .

# Install dependencies with UV (much faster than pip)
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "run.py"]

# Production stage
FROM base as production

# Set production environment
ENV ENVIRONMENT=production
ENV DEBUG=false

# Copy only necessary files for production
COPY --from=base /app /app

# Install gunicorn for production with UV
RUN uv pip install --system gunicorn

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "sync", "mcp_server.app:create_app()"]
