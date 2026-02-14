BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

curl -X POST ${BASE_URL}/reload_docs \
  -H "Content-Type: application/json"