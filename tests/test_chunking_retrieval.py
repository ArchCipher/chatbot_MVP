"""Integration tests: chunking + indexing + retrieval.

Verifies that after splitting on ## headers and indexing into ChromaDB,
queries return the expected chunks. Uses in-memory Chroma (EphemeralClient).
Requires chromadb (and langchain-text-splitters) installed.

Run from project root (with venv activated):
  python -m unittest tests.test_chunking_retrieval -v
"""

import os
import tempfile
import threading
import unittest

import chromadb
from pathlib import Path

from chroma.indexer import ChromaIndexer
from chroma.hash_manager import FileHashManager
from chroma.text_splitter import TextSplitter
from chroma.retriever import ChromaRetriever


class TestChunkingRetrieval(unittest.TestCase):
    """Index a small markdown doc split by ## headers, then check retrieval."""

    def setUp(self):
        self.client = chromadb.EphemeralClient()
        self.collection = self.client.get_or_create_collection("test_chunking")
        self.lock = threading.Lock()
        self.text_splitter = TextSplitter(chunk_size=2000, chunk_overlap=200)
        self.temp_dir = tempfile.mkdtemp()
        hash_path = Path(self.temp_dir) / "file_hashes.json"
        self.hash_manager = FileHashManager(hash_path)
        self.indexer = ChromaIndexer(
            self.collection, self.lock, self.text_splitter, self.hash_manager
        )
        self.retriever = ChromaRetriever(self.collection)

    def tearDown(self):
        for f in Path(self.temp_dir).iterdir():
            f.unlink()
        os.rmdir(self.temp_dir)

    def test_query_returns_chunk_containing_queried_topic(self):
        content = """## Apples

Apples are fruit. They grow on trees. Red and green varieties.

## Bananas

Bananas are yellow. They are rich in potassium.

## Oranges

Oranges are citrus. They contain vitamin C.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8", dir=self.temp_dir
        ) as f:
            f.write(content)
            doc_path = f.name
        try:
            result = self.indexer.index_files([doc_path])
            self.assertEqual(len(result.errors), 0)
            self.assertEqual(len(result.files), 1)

            results = self.retriever.get_query_results("bananas and potassium", n_results=3)
            self.assertGreater(len(results), 0)
            contents = [r["content"] for r in results]
            self.assertTrue(
                any("Bananas" in c and "potassium" in c for c in contents),
                f"Expected chunk about Bananas/potassium in {contents}",
            )
        finally:
            os.unlink(doc_path)

    def test_different_queries_return_relevant_sections(self):
        content = """## Security rules

Use strong passwords. Enable 2FA.

## Performance tips

Cache results. Use indexes.

## Deployment

Run in Docker. Set env vars.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8", dir=self.temp_dir
        ) as f:
            f.write(content)
            doc_path = f.name
        try:
            self.indexer.index_files([doc_path])
            security_results = self.retriever.get_query_results("security passwords 2FA", n_results=3)
            deploy_results = self.retriever.get_query_results("Docker deployment", n_results=3)
            security_contents = " ".join(r["content"] for r in security_results)
            deploy_contents = " ".join(r["content"] for r in deploy_results)
            self.assertIn("Security", security_contents)
            self.assertTrue("password" in security_contents or "2FA" in security_contents)
            self.assertIn("Deployment", deploy_contents)
            self.assertIn("Docker", deploy_contents)
        finally:
            os.unlink(doc_path)


if __name__ == "__main__":
    unittest.main()
