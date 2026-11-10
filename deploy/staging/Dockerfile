# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# Compile only the dedicated staging artifact; never run a Vite review server.
FROM node:24.22.1-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build:staging

# Keep the already tested Python minor version separate from the legacy image.
FROM python:3.14.4-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --create-home moulai \
    && mkdir -p /var/data/moulai-staging/private \
    && chown -R moulai:moulai /var/data/moulai-staging
COPY app/ ./app/
COPY migration_support/ ./migration_support/
COPY scripts/run_staging.py ./scripts/run_staging.py
COPY deploy/staging/target.json ./deploy/staging/target.json
COPY --from=frontend /build/frontend/staging-dist/ ./frontend/staging-dist/
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    MOULAI_STAGING_TARGET_FILE=/app/deploy/staging/target.json \
    MOULAI_STAGING_DATA_DIR=/var/data/moulai-staging
USER moulai
# Requires reviewed secrets, isolated OIDC and runtime database role before serving.
CMD ["python", "-I", "-B", "scripts/run_staging.py", "--serve"]
