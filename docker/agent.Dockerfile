FROM python:3.13-slim AS base

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

COPY packages/agent/ .
RUN uv pip install --system .
ENV PYTHONPATH=/app/src
RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "-m", "daily_ai_agent.api_server"]

FROM base AS production
ENV ENVIRONMENT=production DEBUG=false
USER root
RUN uv pip install --system gunicorn
USER appuser
# --timeout 120: plan_outing calls Navi, whose planner+critic loop runs ~45-50s,
# well past gunicorn's 30s default — which was killing the worker mid-request and
# leaving the chat with no response. gthread + threads so one long plan doesn't
# block concurrent requests (calendar, todos, health) on the single worker.
CMD ["gunicorn", "--bind", "0.0.0.0:8001", "--workers", "1", "--worker-class", "gthread", "--threads", "8", "--timeout", "120", "daily_ai_agent.api_server:create_app()"]
