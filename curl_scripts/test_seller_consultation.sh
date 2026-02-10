#!/usr/bin/env bash
# Complete seller consultation flow (session_id=2). Prints input, output, OK/KO per step.

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
SESSION_ID=2
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

echo "=== Seller consultation (session_id=$SESSION_ID) ==="
run_step "I want to sell electricity" "consult"
run_step "Selling surplus solar" "name"
run_step "Jane Doe" "email"
run_step "jane@example.com" "phone"
run_step "+1-555-123-4567" "company"
run_step "Green Energy Co" "website"
run_step "https://greenenergy.example.com" "address"
run_step "123 Main St, City" "additional"
run_step "None" "Thank you"

echo "=== Result: ${PASS} OK, ${FAIL} KO ==="
[[ $FAIL -eq 0 ]]
