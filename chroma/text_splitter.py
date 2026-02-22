"""Chunking: split on chapter headers then by size with RecursiveCharacterTextSplitter"""

import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

class TextSplitter:
    """Splits markdown into sections on chapter headers, sub-splits sections over chunk_size"""

    DEFAULT_CHUNK_SIZE = 2000
    DEFAULT_CHUNK_OVERLAP = 200

    def __init__(self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def split(self, file):
        """
        Read .md file, split on headers, then by chunk_size/overlap.
        Return list of chunk strings.
        """
        if not file.endswith(".md"):
            raise ValueError(f"File {file} is not a markdown file")
        with open(file, "r", encoding="utf-8") as f:
            text = f.read()
        sections = self._split_on_headers(text)
        if not sections:
            sections = [text]
        all_chunks = []
        for section in sections:
            section_chunks = self.text_splitter.split_text(section)
            all_chunks.extend(section_chunks)
        return all_chunks

    @staticmethod
    def _split_on_headers(text):
        """Split on chapter-level headers into sections"""
        header_pattern = r'^##\s+\*\*\d+\s'
        sections = []
        current_section = []
        lines = text.split('\n')
        for line in lines:
            match = re.match(header_pattern, line)
            if not match:
                current_section.append(line)
                continue
            # if header matches
            if current_section: # add current section to sections
                sections.append('\n'.join(current_section))
            # start new section
            current_section = [line]
        if current_section: # add last section
            sections.append('\n'.join(current_section))
        return sections
