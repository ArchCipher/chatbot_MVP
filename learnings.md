# Chatbot – issues & learnings

## 1. Indexing / duplicates

**Issue:** Same file indexed twice, duplicate results.

**Cause:** Inconsistent path representation (sometimes `Path(filename)`, sometimes plain `filename`) → different `source` and different MD5 → same content stored under different ids.

**Fix:** Normalised path everywhere: `norm_file = str(Path(file).resolve())` for hashing and for metadata `source`. Used it in both add and (when applicable) skip/update paths.

**Re-index without wiping DB:** If only code changes (e.g. adding `rule_id`), re-run index; existing chunks get metadata updated via `collection.update()`. Only delete `chroma_db` when **chunk_size**, **chunk_overlap**, or split logic changes.

---

## 2. Chunking & retrieval

**Issue:** Small chunks (500), large PDFs → poor retrieval (distance > 1, content split across chunks).

**Tried:**
- Larger size: `chunk_size 2000`, `overlap 200`, `n_results 8` → 487 chunks; still high distance and split content.
- Split on all markdown headers `#`, `##`, `###` → 1399 chunks, avg length 593 (too many small chunks).
- Split on chapter-level only: pattern `^##\s+\*\*\d+\s` (e.g. `## **2 Preprocessor**`), not `## **2.1 PRE30-C**` → ~15 sections per doc, then `RecursiveCharacterTextSplitter` sub-splits by size → 489 + 349 chunks, avg ~1770. Avoids ~1800 chunks from splitting on every `##`.

**Issue:** Semantic search didn’t always return the specific rule-definition chunk first (e.g. PRE30-C, DCL30-C).

**Fix:** Rule-id metadata + hybrid retrieval:
- On index: detect rule headers (`## **N.M RULE-ID-C.`), set `rule_id` in chunk metadata.
- On query: if message contains a rule ID, run `collection.get(where={"rule_id": rule_id})` and prepend those chunks (distance 0.0); then `collection.query(n_results=n_results*2)`; merge with data deduplication by doc_id and trim to `n_results` (2× so that after dropping duplicates we still fill the list).
- Try/except only around the rule boost so optional path fails silently; semantic query failures propagate.

**Config change:** After changing `chunk_size` / `chunk_overlap` or split logic, run `rm -rf chroma_db` (or equivalent) and re-index so all chunks are recreated with the new strategy.

---
