#!/usr/bin/env bash
# Test validation: invalid email, phone, percentages (session_id=3). Prints input, output, OK/KO.

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
SESSION_ID=3
PASS=0
FAIL=0

run_step() {
  local msg="$1"
  local expected="$2"
  echo "---"
  echo "Input: $msg"
  local response
  response=$(curl -s -X POST "${BASE_URL}/chat" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"$msg\", \"session_id\": ${SESSION_ID}}")
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

# Setup: buyer, topic, name (no check, just advance)
curl -s -X POST "${BASE_URL}/chat" -H "Content-Type: application/json" -d "{\"message\": \"I want to buy\", \"session_id\": ${SESSION_ID}}" > /dev/null
curl -s -X POST "${BASE_URL}/chat" -H "Content-Type: application/json" -d "{\"message\": \"Test\", \"session_id\": ${SESSION_ID}}" > /dev/null
curl -s -X POST "${BASE_URL}/chat" -H "Content-Type: application/json" -d "{\"message\": \"Test User\", \"session_id\": ${SESSION_ID}}" > /dev/null

echo "=== Invalid inputs (session_id=$SESSION_ID) ==="
run_step "notanemail" "valid email"
run_step "test@example.com" "phone"
run_step "123" "phone"
run_step "555-abc-defg" "phone"
run_step "555-123-4567" "company"
# Fast-forward to product_config
curl -s -X POST "${BASE_URL}/chat" -H "Content-Type: application/json" -d "{\"message\": \"Co\", \"session_id\": ${SESSION_ID}}" > /dev/null
curl -s -X POST "${BASE_URL}/chat" -H "Content-Type: application/json" -d "{\"message\": \"https://c.com\", \"session_id\": ${SESSION_ID}}" > /dev/null
curl -s -X POST "${BASE_URL}/chat" -H "Content-Type: application/json" -d "{\"message\": \"Addr\", \"session_id\": ${SESSION_ID}}" > /dev/null
curl -s -X POST "${BASE_URL}/chat" -H "Content-Type: application/json" -d "{\"message\": \"No\", \"session_id\": ${SESSION_ID}}" > /dev/null

run_step "nuclear" "solar"
run_step "solar" "fixed price"
run_step "fifty" "number"
run_step "50" "market price"
run_step "40" "100"
run_step "50" "market price"
run_step "50" "renewable"
run_step "101" "between 0 and 100"

echo "=== Result: ${PASS} OK, ${FAIL} KO ==="
[[ $FAIL -eq 0 ]]
