#!/usr/bin/env bash
#
# Applies database migrations, then execs the given command.
#
# Running migrations here is fine for a single-replica API in development. In
# Kubernetes this becomes a Job or an initContainer instead, because N replicas
# starting at once would all race to migrate. That change is made in Phase 3.

set -euo pipefail

echo "{\"level\":\"INFO\",\"service\":\"api-entrypoint\",\"message\":\"applying migrations\"}"

# Retry: on a cold start Postgres may still be initialising even though the
# container is up.
attempt=1
max_attempts=10
until alembic upgrade head; do
  if [ "${attempt}" -ge "${max_attempts}" ]; then
    echo "{\"level\":\"ERROR\",\"service\":\"api-entrypoint\",\"message\":\"migrations failed after ${max_attempts} attempts\"}" >&2
    exit 1
  fi
  echo "{\"level\":\"WARNING\",\"service\":\"api-entrypoint\",\"message\":\"migration attempt ${attempt} failed, retrying\"}" >&2
  attempt=$((attempt + 1))
  sleep 3
done

echo "{\"level\":\"INFO\",\"service\":\"api-entrypoint\",\"message\":\"migrations complete, starting server\"}"

# exec replaces PID 1 so SIGTERM reaches uvicorn directly and graceful
# shutdown actually works during rolling updates.
exec "$@"
