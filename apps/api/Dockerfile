# syntax=docker/dockerfile:1
# Porterchain API (FastAPI). Build context is the repo root:
#   docker build -f apps/api/Dockerfile -t pcd-api .

FROM python:3.13-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Platform packages are installed editable via apps/api/requirements.txt
# (paths are relative to apps/api), so copy them alongside the API source.
COPY shared/python ./shared/python
COPY services/python ./services/python
COPY services/fleetbase-adapter ./services/fleetbase-adapter
COPY services/fleetbase ./services/fleetbase
COPY services/pricing-engine ./services/pricing-engine
COPY services/event-bus ./services/event-bus
COPY services/driver-platform ./services/driver-platform
COPY apps/api ./apps/api

WORKDIR /app/apps/api
RUN pip install --upgrade pip && pip install -r requirements.txt

ENV PYTHONPATH=/app/apps/api/src \
    DATABASE_URL=sqlite:////data/porterchain.db \
    APP_ENV=production \
    APP_DEBUG=false

# Persist the SQLite database outside the image layer.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8001/health || exit 1

CMD ["uvicorn", "porterchain_api.main:app", "--host", "0.0.0.0", "--port", "8001"]
