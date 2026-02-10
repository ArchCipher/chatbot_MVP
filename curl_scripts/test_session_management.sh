#!/usr/bin/env bash
# Test session persistence: session_id=1 vs 99. Prints input, output, OK/KO.

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
SESSION_ID=1
PASS=0
FAIL=0

run_step() {
  local msg="$1"
  local sid="$2"
  local expected="$3"
  echo "---"
  echo "Input: $msg (session_id=$sid)"
  local response
  response=$(curl -s -X POST "${BASE_URL}/chat" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"$msg\", \"session_id\": ${sid}}")
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

echo "=== Session management ==="
run_step "Hello" 1 "buy electricity or sell"
run_step "I want to buy" 1 "consult"
run_step "I need a consultation" 1 "consult"
run_step "Pricing" 1 "name"
run_step "Hi" 99 "buy electricity or sell"
run_step "John" 1 "email"

echo "=== Result: ${PASS} OK, ${FAIL} KO ==="
[[ $FAIL -eq 0 ]]
