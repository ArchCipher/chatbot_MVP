#!/usr/bin/env bash
# Test all questions for POST /chat endpoint

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

# Array of test questions
questions=(
  "How many documents do you have in your database?"
  "give me a concise summary of sei C coding standard in 5 lines within 50 words"
  "give me a concise summary of sei C++ coding standard in 5 lines within 50 words"
  "Give me 5 rules of sei C++ coding standard that i should follow for safe coding"
  "Give me 5 rules of sei C coding standard that i should follow for safe coding"
  "Give me 5 C coding standard that i should follow"
  "What is PRE30-C?"
  "What is DCL30-C?"
  "Explain EXP34-C"
)

echo "=========================================="
echo "Testing ${#questions[@]} questions"
echo "=========================================="
echo ""

# Counter for test number
test_num=1

for question in "${questions[@]}"; do
  echo "--- Test $test_num ---"
  echo "Question: $question"
  echo ""
  echo "Response:"
  
  curl -s -X POST ${BASE_URL}/chat \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"$question\", \"session_id\": 1}" | \
    python3 -m json.tool 2>/dev/null || \
    curl -s -X POST ${BASE_URL}/chat \
      -H "Content-Type: application/json" \
      -d "{\"message\": \"$question\", \"session_id\": 1}"
  
  echo ""
  echo ""
  
  # Small delay between requests
  sleep 1
  
  ((test_num++))
done

echo "=========================================="
echo "All tests completed"
echo "=========================================="