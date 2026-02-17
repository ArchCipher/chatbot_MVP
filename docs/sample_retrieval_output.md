# Sample retrieval output

Sanitized excerpt from retrieval pipeline for query `"What is PRE30-C?"` with `N_RESULTS=5`. Rule boost runs first; semantic search fills the rest after dedup.

```json
{
    "id": "rule_boost_applied",
    "message": "Rule ID boost applied",
    "data": {
        "query": "What is PRE30-C?",
        "rule_id": "PRE30-C",
        "chunks_found": 1
        }
}
{
    "id": "query_summary",
    "message": "Query summary",
    "data": {
        "query": "What is PRE30-C?",
        "total_chunks_retrieved": 5,
        "distances": [0.0, 1.28, 1.33, 1.33, 1.34], "rules_found_in_chunks": ["PRE30-C"],
        "query_contains_rule": true
        }
}
```

First chunk has `distance: 0.0` (rule definition); remaining chunks are from semantic search.
