# syntax=docker/dockerfile:1
#
# Multi-stage build. The builder installs dependencies into an isolated prefix
# and only the resulting site-packages are copied into the runtime stage, so no
# compilers or pip caches ship in the final image.

FROM python:3.14-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# ---------- builder ----------
FROM base AS builder
COPY requirements/ ./requirements/
RUN pip install --prefix=/install --no-compile -r requirements/api.txt

# ---------- runtime ----------
FROM base AS runtime

# Non-root user. A fixed high UID keeps this compatible with Kubernetes
# runAsNonRoot/runAsUser security contexts later.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin sentinel

COPY --from=builder /install /usr/local

COPY libs/ ./libs/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY services/api/ ./services/api/

# sentinel_core lives in libs/, which is not an installed package.
ENV PYTHONPATH=/app/libs:/app/services/api

# Numeric, not the username: resolvable without an /etc/passwd lookup and the
# same form Kubernetes securityContext.runAsUser will compare against later.
USER 10001
EXPOSE 8000

# Liveness only; readiness is checked by the orchestrator via /ready. Exec
# (JSON) form so no shell is spawned to interpret it.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status==200 else 1)"]

ENTRYPOINT ["/app/services/api/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
