"""RAG client: coordinates ChromaDB collection, indexer, and retriever.

Discovers PDF/MD under collection_path, converts PDFs to MD, delegates
chunking/indexing to ChromaIndexer and retrieval to ChromaRetriever.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import chromadb
import pymupdf4llm

from chroma.hash_manager import FileHashManager
from chroma.indexer import ChromaIndexer
from chroma.models import CollectionResult
from chroma.retriever import ChromaRetriever
from chroma.text_splitter import TextSplitter

logger = logging.getLogger("RagClient")


class RagClient:
    """RAG client: indexing from collection_path and retrieval from ChromaDB."""

    MAX_RECURSION_DEPTH = 3

    def __init__(
        self,
        name: str = "my-collection",
        persistent_storage: str = "chroma_db",
        collection_path: str = "source_docs",
        hash_filename: str = "file_hashes.json",
    ) -> None:
        """
        Create ChromaDB client, collection, indexer, and retriever.
        Hash file is stored under persistent_storage.
        """
        client = chromadb.PersistentClient(path=persistent_storage)
        collection = client.get_or_create_collection(name)
        lock = threading.Lock()
        # instantiate text splitter
        text_splitter = TextSplitter()
        # create hash file path and instantiate hash manager
        hash_file_path = Path(persistent_storage) / Path(hash_filename)
        hash_manager = FileHashManager(hash_file_path)
        # instantiate indexer and retriever
        self.indexer = ChromaIndexer(collection, lock, text_splitter, hash_manager)
        self.retriever = ChromaRetriever(collection)
        # store collection path
        self.collection_path = collection_path

    def get_context(self, message: str, n_results: int = 50) -> str:
        """Return formatted context string from top n_results chunks for message."""
        results = self.retriever.get_query_results(message, n_results)
        return self.retriever.get_context(results)

    def reload_collection(self) -> CollectionResult:
        """
        Discover files under collection_path, index changed ones.
        Returns CollectionResult.
        """
        result = self.list_files(self.collection_path)
        if not result.files:
            result.errors.append("No files to index")
            return result
        return self.indexer.index_files(result.files)

    def list_files(self, path: Path | str) -> CollectionResult:
        """Recursively list .md paths under path and convert PDFs to .md."""
        files, errors, pdfs_to_convert = self._discover_files(path, 0)
        if pdfs_to_convert:
            converted_files = self._extract_text_from_pdfs(pdfs_to_convert)
            files.extend(converted_files)
        return CollectionResult(files=files, errors=errors)

    def _discover_files(
        self, path: Path | str, depth: int = 0
    ) -> tuple[list[str], list[str], list[str]]:
        """
        Recursively list .md paths under path
        Returns (md file list, errors, pdfs to convert).
        """
        files = []
        errors = []
        pdfs_to_convert = []
        md_from_pdfs = set()
        ret = files, errors, pdfs_to_convert
        if depth > self.MAX_RECURSION_DEPTH:
            # logger.error(f"Max depth reached: {self.MAX_RECURSION_DEPTH}")
            errors.append(f"Max depth reached: {self.MAX_RECURSION_DEPTH}")
            return ret
        if not isinstance(path, Path):
            path = Path(path)
        if not path.exists():
            # logger.error(f"Collection path not found: {path}")
            errors.append(f"Collection path not found: {path}")
            return ret
        for filepath in path.iterdir():
            if filepath.is_dir():
                subdir = self._discover_files(Path(filepath), depth + 1)
                self._merge_discovered_files(files, errors, pdfs_to_convert, subdir)
                continue
            if self._valid_file(filepath):
                self._categorise_file(filepath, files, pdfs_to_convert, md_from_pdfs)
        return ret

    @staticmethod
    def _merge_discovered_files(
        files: list[str],
        errors: list[str],
        pdfs_to_convert: list[str],
        subdir: tuple[list[str], list[str], list[str]],
    ) -> None:
        subdir_files, subdir_errors, subdir_pdfs = subdir
        files.extend(subdir_files)
        errors.extend(subdir_errors)
        pdfs_to_convert.extend(subdir_pdfs)

    @staticmethod
    def _categorise_file(
        filepath: Path,
        files: list[str],
        pdfs_to_convert: list[str],
        md_from_pdfs: set[str],
    ) -> None:
        """Append file to files (as .md path) or to pdfs_to_convert, and track md from PDFs."""
        if filepath.suffix.lower() == ".md":
            md_file = str(filepath.resolve())
            if md_file not in md_from_pdfs and md_file not in files:
                files.append(md_file)
            return
        # if pdf file, check if .md file exists and is newer than the pdf
        md_path = filepath.with_suffix(".md")
        if not (
            md_path.exists() and filepath.stat().st_mtime <= md_path.stat().st_mtime
        ):
            pdfs_to_convert.append(str(filepath.resolve()))
            return
        md_file = str(md_path.resolve())
        if md_file not in files:
            files.append(md_file)
        md_from_pdfs.add(md_file)  # set is idempotent

    @staticmethod
    def _valid_file(filepath: Path) -> bool:
        """Returns True if path is a file with .pdf or .md extension."""
        if not filepath.is_file():
            return False
        extension = filepath.suffix.lower()
        return extension in [".pdf", ".md"]

    def _extract_text_from_pdfs(self, pdfs: list[str]) -> list[str]:
        """Convert PDFs to markdown in parallel"""
        converted_files = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_pdf = {
                executor.submit(self._extract_text_from_pdf, pdf): pdf for pdf in pdfs
            }
            for future in as_completed(future_to_pdf):
                try:
                    md_file = future.result()
                    if md_file:
                        converted_files.append(md_file)
                except Exception as e:
                    pdf = future_to_pdf[future]
                    logger.error(f"Error extracting text from {pdf}: {e}")
        return converted_files

    @staticmethod
    def _extract_text_from_pdf(pdf: str) -> str | None:
        """Convert one PDF to markdown"""
        extension = Path(pdf).suffix.lower()
        if extension != ".pdf":
            return None
        try:
            md = pymupdf4llm.to_markdown(pdf, header=False, footer=False)
            if not isinstance(md, str):
                return None
            md_path = Path(pdf).with_suffix(".md")
            md_path.write_text(md, encoding="utf-8")
            return str(md_path.resolve())
        except Exception:
            return None
