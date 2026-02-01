FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv-cache

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

COPY packages/server/pyproject.toml packages/server/requirements.txt ./
RUN uv pip install --system -r requirements.txt

COPY packages/server/ .
RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "run.py"]

FROM base AS production
ENV ENVIRONMENT=production DEBUG=false
# uvicorn is already installed via requirements.txt
CMD ["uvicorn", "mcp_server.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
