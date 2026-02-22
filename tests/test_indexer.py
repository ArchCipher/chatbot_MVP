"""Unit tests for chroma indexer.

Run from project root (with deps installed):
  python -m unittest tests.test_indexer -v
"""

import unittest

from chroma.indexer import ChromaIndexer


class TestGenerateMd5Hash(unittest.TestCase):
    def test_deterministic_same_inputs(self):
        out1 = ChromaIndexer._generate_md5_hash("hello", "/path/to/file.md")
        out2 = ChromaIndexer._generate_md5_hash("hello", "/path/to/file.md")
        self.assertEqual(out1, out2)

    def test_different_content_different_hash(self):
        a = ChromaIndexer._generate_md5_hash("chunk A", "/f.md")
        b = ChromaIndexer._generate_md5_hash("chunk B", "/f.md")
        self.assertNotEqual(a, b)

    def test_different_source_different_hash(self):
        a = ChromaIndexer._generate_md5_hash("same text", "/path/a.md")
        b = ChromaIndexer._generate_md5_hash("same text", "/path/b.md")
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
