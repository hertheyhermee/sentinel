#!/usr/bin/env bash
#
# End-to-end verification of a running stack.
#
# Proves the whole pipeline works, not just that containers started:
#   api accepts a monitor -> scheduler enqueues it -> worker probes it
#   -> a result lands in Postgres -> the SLO endpoint reports it.
#
# This is the same shape of check that runs as the integration gate in CI.

set -euo pipefail

API="${API:-http://localhost:8000}"
TIMEOUT="${TIMEOUT:-90}"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

# macOS ships no `timeout` by default (it is a GNU coreutils command), while
# Linux CI runners have it. wait_until polls in pure bash so this script works
# identically on a contributor's Mac and in GitHub Actions.
wait_until() {
  local description="$1" seconds="$2"
  shift 2
  local waited=0
  until "$@" >/dev/null 2>&1; do
    waited=$((waited + 2))
    if [ "${waited}" -ge "${seconds}" ]; then
      fail "${description} did not happen within ${seconds}s"
    fi
    sleep 2
  done
}

echo "1/5 waiting for liveness"
wait_until "api liveness" "${TIMEOUT}" curl -fsS "${API}/health"
echo "     ok"

echo "2/5 waiting for readiness (postgres + redis reachable)"
wait_until "api readiness" "${TIMEOUT}" curl -fsS "${API}/ready"
curl -fsS "${API}/ready" | python3 -m json.tool
echo "     ok"

echo "3/5 creating a monitor with a short interval"
MONITOR_ID=$(
  curl -fsS -X POST "${API}/api/monitors" \
    -H 'Content-Type: application/json' \
    -d '{"name":"smoke","url":"https://example.com","interval_seconds":10}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'
) || fail "could not create monitor"
echo "     created monitor ${MONITOR_ID}"

echo "4/5 waiting for the worker to record a probe result"
has_results() {
  local count
  count=$(curl -fsS "${API}/api/monitors/${MONITOR_ID}/results" \
    | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')
  [ "${count}" -gt 0 ]
}
wait_until "a probe result" "${TIMEOUT}" has_results

curl -fsS "${API}/api/monitors/${MONITOR_ID}/results" | python3 -m json.tool
echo "     ok"

echo "5/5 checking the SLO report and metrics"
curl -fsS "${API}/api/monitors/${MONITOR_ID}/slo" | python3 -m json.tool

curl -fsS "${API}/metrics" | grep -q 'sentinel_probes_total' \
  || fail "sentinel_probes_total missing from /metrics"
echo "     ok"

echo
echo "SMOKE PASSED: scheduler -> queue -> worker -> database -> api all working"
