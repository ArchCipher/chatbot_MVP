"""Unit tests for chunking: header-based split and section boundaries.

Run from project root:
  python -m unittest tests.test_text_splitter -v
"""

import os
import tempfile
import unittest

from chroma.text_splitter import TextSplitter


class TestSplitOnHeaders(unittest.TestCase):
    """Test _split_on_headers splits only on level-2 (## ) markdown headers."""

    def test_empty_string_returns_one_empty_section(self):
        sections = TextSplitter._split_on_headers("")
        self.assertEqual(sections, [""])

    def test_no_header_returns_one_section(self):
        text = "Some intro.\n\nMore text."
        sections = TextSplitter._split_on_headers(text)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0], text)

    def test_single_header_at_start_returns_one_section(self):
        text = "## Only section\n\nContent here."
        sections = TextSplitter._split_on_headers(text)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0], text)

    def test_two_sections_split_at_second_header(self):
        text = "## First\n\nContent one.\n\n## Second\n\nContent two."
        sections = TextSplitter._split_on_headers(text)
        self.assertEqual(len(sections), 2)
        self.assertIn("First", sections[0])
        self.assertIn("Content one", sections[0])
        self.assertIn("Second", sections[1])
        self.assertIn("Content two", sections[1])

    def test_three_sections(self):
        text = "## A\n\nA content.\n\n## B\n\nB content.\n\n## C\n\nC content."
        sections = TextSplitter._split_on_headers(text)
        self.assertEqual(len(sections), 3)
        self.assertEqual(sections[0].strip().split("\n")[0], "## A")
        self.assertEqual(sections[1].strip().split("\n")[0], "## B")
        self.assertEqual(sections[2].strip().split("\n")[0], "## C")

    def test_intro_without_header_then_sections(self):
        text = "Intro line.\n\n## First\n\nContent."
        sections = TextSplitter._split_on_headers(text)
        self.assertEqual(len(sections), 2)
        # First section: lines before first ## joined by newline; blank line yields one \\n
        self.assertEqual(sections[0], "Intro line.\n")
        self.assertIn("## First", sections[1])
        self.assertIn("Content", sections[1])

    def test_level3_header_not_split(self):
        text = "## Section One\n\n### Subsection\n\nContent."
        sections = TextSplitter._split_on_headers(text)
        self.assertEqual(len(sections), 1)
        self.assertIn("### Subsection", sections[0])
        self.assertIn("Content", sections[0])

    def test_header_like_in_line_not_split(self):
        text = "Line with ## not at start.\n\n## Real\n\nContent."
        sections = TextSplitter._split_on_headers(text)
        self.assertEqual(len(sections), 2)
        self.assertIn("## not at start", sections[0])
        self.assertIn("## Real", sections[1])


class TestSplitFile(unittest.TestCase):
    """Test split() produces chunks that respect section boundaries."""

    def test_small_sections_produce_one_chunk_per_section(self):
        splitter = TextSplitter(chunk_size=2000, chunk_overlap=200)
        content = "## Alpha\n\nShort content.\n\n## Beta\n\nAlso short."
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            path = f.name
        try:
            chunks = splitter.split(path)
            self.assertGreaterEqual(len(chunks), 2)
            self.assertTrue(
                any("Alpha" in c and "Short content" in c for c in chunks),
                "One chunk should contain Alpha section",
            )
            self.assertTrue(
                any("Beta" in c and "Also short" in c for c in chunks),
                "One chunk should contain Beta section",
            )
        finally:
            os.unlink(path)

    def test_non_md_raises(self):
        splitter = TextSplitter()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = f.name
        try:
            with self.assertRaises(ValueError) as ctx:
                splitter.split(path)
            self.assertIn("not a markdown file", str(ctx.exception))
        finally:
            os.unlink(path)
