"""
Benchmark indexing (sequential). Clears the collection and hashes, runs index once, prints time.

Run from project root (same COLLECTION_PATH, PERSISTENT_STORAGE as .env):

  python -m scripts.benchmark_indexing

Uses existing source_docs (and converts PDFs once). Destructive: wipes chroma_db
and file_hashes for the collection, then re-indexes once.
"""

import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

# Project root for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from chroma import RagClient


def main():
    rag = RagClient(
        name=os.getenv("COLLECTION_NAME", "my-collection"),
        persistent_storage=os.getenv("PERSISTENT_STORAGE", "chroma_db"),
        collection_path=os.getenv("COLLECTION_PATH", "source_docs"),
    )
    result = rag.list_files(rag.collection_path)
    files = result.files
    if not files:
        print("No files to index. Check COLLECTION_PATH and source_docs.")
        return
    if result.errors:
        print("Warnings:", result.errors)
    print(f"Files to index: {len(files)}")
    print("Clearing collection and hashes...")
    rag.indexer.clear()
    print("Indexing (sequential)...")
    t0 = time.perf_counter()
    r = rag.indexer.index_files(files)
    elapsed = time.perf_counter() - t0
    print(f"  Indexed {len(r.files)} files in {elapsed:.2f}s")
    print(f"Done. {elapsed:.2f}s")


if __name__ == "__main__":
    main()
