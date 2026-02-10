#!/usr/bin/env bash
# Test GET / health endpoint

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
PASS=0
FAIL=0

run_step() {
  local expected="$1"
  echo "---"
  echo "Input: GET ${BASE_URL}/"
  local response
  response=$(curl -s "${BASE_URL}/")
  echo "Output: $response"
  if echo "$response" | grep -q "$expected"; then
    echo "OK"
    ((PASS++)) || true
  else
    echo "KO (expected substring: $expected)"
    ((FAIL++)) || true
  fi
  echo ""
}

echo "=== Test GET / ==="
run_step "Hello World"

echo "=== Result: ${PASS} OK, ${FAIL} KO ==="
[[ $FAIL -eq 0 ]]
