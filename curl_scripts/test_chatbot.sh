#!/usr/bin/env bash
# Test POST /chat endpoint

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

curl -X POST ${BASE_URL}/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the name on the CV", "session_id": 1}'