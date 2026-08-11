# syntax=docker/dockerfile:1
FROM python:3.14-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# ---------- builder ----------
FROM base AS builder
COPY requirements/ ./requirements/
RUN pip install --prefix=/install --no-compile -r requirements/worker.txt

# ---------- runtime ----------
FROM base AS runtime
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin sentinel

COPY --from=builder /install /usr/local
COPY libs/ ./libs/
COPY services/worker/ ./services/worker/

ENV PYTHONPATH=/app/libs

USER sentinel

# Prometheus scrape port for probe metrics.
EXPOSE 9101

CMD ["python", "services/worker/worker.py"]
