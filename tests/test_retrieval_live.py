"""Retrieval tests against your existing ChromaDB (persistent storage).

Uses the same collection and chunking as the running app. Run only when you have
indexed docs (e.g. CERT rules in source_docs) and want to verify retrieval returns
the right content.

Set TEST_USE_REAL_DB=1 to run; otherwise tests are skipped.

  TEST_USE_REAL_DB=1 python -m unittest tests.test_retrieval_live -v

Uses .env (load_dotenv) for PERSISTENT_STORAGE, COLLECTION_NAME, COLLECTION_PATH.
"""

import os
import unittest

from dotenv import load_dotenv

load_dotenv()

SKIP_LIVE = not os.getenv("TEST_USE_REAL_DB")


@unittest.skipIf(SKIP_LIVE, "Set TEST_USE_REAL_DB=1 to run retrieval against existing DB")
class TestRetrievalFromExistingDB(unittest.TestCase):
    """Test retrieval from the real persistent ChromaDB and collection."""

    @classmethod
    def setUpClass(cls):
        from chroma.chroma import RagClient

        cls.client = RagClient(
            name=os.getenv("COLLECTION_NAME", "my-collection"),
            persistent_storage=os.getenv("PERSISTENT_STORAGE", "chroma_db"),
            collection_path=os.getenv("COLLECTION_PATH", "source_docs"),
        )

    def test_retrieval_returns_non_empty_context(self):
        """Query returns some context (smoke test)."""
        context = self.client.get_context("What are the main guidelines?", n_results=5)
        self.assertIsInstance(context, str)
        self.assertGreater(len(context.strip()), 0, "Context should not be empty")

    def test_rule_query_includes_rule_chunk_first(self):
        """For a query that names a rule ID (e.g. PRE30-C), results should include a chunk about that rule."""
        message = "What is PRE30-C?"
        results = self.client.retriever.get_query_results(message, n_results=5)
        self.assertGreater(len(results), 0, "Should return at least one chunk")
        contents = [r["content"] for r in results]
        self.assertTrue(
            any("PRE30-C" in c or "PRE30" in c for c in contents),
            f"At least one chunk should be about the asked rule; got {len(results)} chunks",
        )
        first = results[0]
        if first.get("distance") is not None and first["distance"] == 0.0:
            self.assertIn("PRE30-C", first["content"], "Rule boost chunk should contain rule ID")

    def test_semantic_query_returns_relevant_content(self):
        """A generic semantic query returns context that looks relevant (contains key terms or related text)."""
        context = self.client.get_context("security and macros", n_results=5)
        self.assertGreater(len(context), 0)
        self.assertTrue(
            any(
                term in context.lower()
                for term in ("security", "macro", "guideline", "rule", "code", "pre", "exp")
            ),
            f"Context should be relevant to query; got snippet: {context[:300]}...",
        )


if __name__ == "__main__":
    unittest.main()
