# E2E Test Runner Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install uv

# Copy test files
COPY pyproject.toml .
COPY tests/ tests/

# Install dependencies
RUN uv pip install --system -e .

# Default command runs all tests
CMD ["pytest", "-v", "--tb=short"]
