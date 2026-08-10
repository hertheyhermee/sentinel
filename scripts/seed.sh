#!/usr/bin/env bash
#
# Creates a handful of example monitors against a running API.
#
# The deliberately failing monitor matters: without any down samples the error
# budget and burn-rate panels stay empty and you cannot tell whether the SLO
# maths actually works.

set -euo pipefail

API="${API:-http://localhost:8000}"

create() {
  local name="$1" url="$2" interval="$3" expected="$4" slo="$5"

  curl -fsS -X POST "${API}/api/monitors" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"${name}\",\"url\":\"${url}\",\"interval_seconds\":${interval},\"expected_status\":${expected},\"slo_target\":${slo}}" \
    >/dev/null && echo "created: ${name}"
}

echo "Seeding monitors against ${API}"

create "GitHub"        "https://github.com"                      30  200 0.999
create "Cloudflare DNS" "https://1.1.1.1"                        30  200 0.999
create "Sentinel self" "http://api:8000/health"                  20  200 0.995
create "Always fails"  "https://httpstat.us/500"                 60  200 0.950

echo
echo "Monitors:"
curl -fsS "${API}/api/monitors" | python3 -m json.tool
