#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# smoke-test.sh - run this 10 minutes before the presentation.
#
# Two jobs:
#   1. confirm the whole path works right now
#   2. WARM THE FUNCTIONS, so the first request the examiner sees is not a
#      1-3 second cold start
#
# Takes about 15 seconds. Needs CAMPUSPULSE_API, OPS_USER, OPS_PASSWORD.
# ---------------------------------------------------------------------------
set -uo pipefail

API="${CAMPUSPULSE_API:-}"
USER="${OPS_USER:-ops@northbridge.edu}"
PASS_WORD="${OPS_PASSWORD:-}"

[ -z "$API" ] && { echo "CAMPUSPULSE_API is not set"; exit 2; }
[ -z "$PASS_WORD" ] && { echo "OPS_PASSWORD is not set"; exit 2; }

fail() { echo "  FAIL: $1"; echo; echo "  Do not start the demo. See docs/learning/20-troubleshooting.md"; exit 1; }

echo
echo "CampusPulse pre-flight  $(date -u +%H:%M:%SZ)"

# 1. reachable, and this call pays the cold start instead of the examiner
START=$(date +%s%N)
CODE=$(curl -s -o /dev/null -w '%{http_code}' "$API/health")
MS=$(( ($(date +%s%N) - START) / 1000000 ))
[ "$CODE" = "200" ] || fail "/health returned $CODE"
echo "  [1/6] API reachable            (${MS}ms - cold start paid here, not on stage)"

# 2. login
TOKEN=$(curl -s -X POST "$API/login" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USER\",\"password\":\"$PASS_WORD\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin).get('id_token',''))" 2>/dev/null)
[ -z "$TOKEN" ] && fail "login failed - check the password, and that the user is permanent and in 'ops'"
echo "  [2/6] login works"

AUTH="Authorization: Bearer $TOKEN"
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# 3. write path, with an event that MUST come back critical
RESP=$(curl -s -X POST "$API/events" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"event_id\":\"smoke-$(date +%s)\",\"building\":\"Library-A\",\"room\":\"A203\",
       \"event_type\":\"occupancy\",\"value\":58,\"unit\":\"people\",
       \"severity\":\"normal\",\"timestamp\":\"$TS\"}")
echo "$RESP" | grep -q '"severity": *"critical"' || fail "ingest did not classify 58 in A203 as critical: $RESP"
echo "  [3/6] ingest works, and the server overruled the client's severity"

# 4-6. read path
curl -s -o /dev/null -w '' -H "$AUTH" "$API/events?limit=5" || fail "/events unreachable"
echo "  [4/6] /events responds"
curl -s -H "$AUTH" "$API/alerts" | grep -q '"alerts"' || fail "/alerts did not return a list"
echo "  [5/6] /alerts responds"
curl -s -H "$AUTH" "$API/stats" | grep -q '"total_events"' || fail "/stats did not return statistics"
echo "  [6/6] /stats responds"

echo
echo "  All six checks passed. Functions are warm. Good to go."
echo
