#!/usr/bin/env bash
# Test POST /index_docs endpoint

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

curl -X POST ${BASE_URL}/index_docs \
  -H "Content-Type: application/json" \
  -d '{"files": ["docs/example.md"]}'