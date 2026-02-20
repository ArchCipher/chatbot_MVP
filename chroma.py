'''
RAG client implementation using ChromaDB.
'''

import hashlib
import json
import logging
import re
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pymupdf.layout
import pymupdf4llm

logger = logging.getLogger("RagClient")

class RagClient:

    MAX_RECURSION_DEPTH = 3

    def __init__(self,
        name: str = "my-collection",
        persistent_storage: str = "./chroma_db",
        collection_path: str = "source_docs",
        hash_filename: str = "./file_hashes.json"
    ):
        client = chromadb.PersistentClient(path=persistent_storage)
        collection = client.get_or_create_collection(name)
        lock = threading.Lock()
        text_splitter = TextSplitter()
        hash_folder = Path(persistent_storage)
        hash_folder.mkdir(parents=True, exist_ok=True)
        hash_file_path = hash_folder / Path(hash_filename)
        hash_manager = FileHashManager(hash_file_path)
        self.indexer = ChromaIndexer(collection, lock, text_splitter, hash_manager)
        self.collection_path = collection_path
        self.retriever = ChromaRetriever(collection)

    def get_context(self, message, n_results=5):
        results = self.retriever.get_query_results(message, n_results)
        return self.retriever.get_context(results)

    def reload_collection(self):
        files = self.list_files(self.collection_path)
        if not files:
            files_indexed, errors = [], ["No files to index"]
        else:
            files_indexed, errors = self.indexer.index_files(files)
        return {
            "status": "success" if not errors else "error",
            "files indexed": files_indexed,
            "errors": errors
        }

    def list_files(self, path: Path | str, depth=0):
        files, pdfs_to_convert, md_files_from_pdfs = self._discover_files(path, depth)
        if pdfs_to_convert:
            self._extract_text_from_pdfs(pdfs_to_convert, files, md_files_from_pdfs)
        return files

    def _discover_files(self, path: Path | str, depth=0):
        if depth > self.MAX_RECURSION_DEPTH:
            raise ValueError(f"Max depth reached: {self.MAX_RECURSION_DEPTH}")
        if not isinstance(path, Path):
            path = Path(path)
        if not path.exists():
            logger.error(f"Collection path not found: {path}")
            return []
        files = []
        pdfs_to_convert = []
        md_files_from_pdfs = set()
        for filepath in path.iterdir():
            if filepath.is_dir():
                files.extend(self.list_files(Path(filepath), depth + 1))
                continue
            self._categorise_file(filepath, files, pdfs_to_convert, md_files_from_pdfs)
        return files, pdfs_to_convert, md_files_from_pdfs

    def _categorise_file(self, filepath, files, pdfs_to_convert, md_files_from_pdfs):
        if not self._validate_file(filepath):
            return
        if filepath.suffix.lower() == ".md":
            # markdown file
            md_file = str(filepath.resolve())
            if md_file not in md_files_from_pdfs:
                files.append(md_file)
            return
        # pdf file
        md_path = filepath.with_suffix(".md")
        if md_path.exists() and filepath.stat().st_mtime <= md_path.stat().st_mtime:
            md_file = str(md_path.resolve())
            if md_file not in files:
                files.append(md_file)
            md_files_from_pdfs.add(md_file)
        else:
            pdfs_to_convert.append(str(filepath.resolve()))     

    def _validate_file(self, filepath: Path):
        if not filepath.is_file():
            return False
        extension = filepath.suffix.lower()
        return extension in [".pdf", ".md"]

    def _extract_text_from_pdfs(self, pdfs, files, md_files_from_pdfs):
        converted_files = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_pdf = {
                executor.submit(self._extract_text_from_pdf, pdf):pdf
                for pdf in pdfs
            }
            for future in as_completed(future_to_pdf):
                pdf = future_to_pdf[future]
                try:
                    if future.result():
                        md_path = Path(pdf).with_suffix(".md")
                        md_file = str(md_path.resolve())
                        if md_file not in md_files_from_pdfs:
                            converted_files.append(md_file)
                except Exception as e:
                    logger.error(f"Error extracting text from {pdf}: {e}")
        for md_file in converted_files:
            files.append(md_file)
            md_files_from_pdfs.add(md_file)

    @staticmethod
    def _extract_text_from_pdf(doc):
        extension = Path(doc).suffix.lower()
        if extension != ".pdf":
            return False
        try:
            md = pymupdf4llm.to_markdown(doc, header=False, footer=False)
            Path(doc).with_suffix(".md").write_text(md, encoding="utf-8")
            return True
        except Exception:
            return False

class FileHashManager:
    def __init__(self, hash_file: Path | str):
        if not isinstance(hash_file, Path):
            hash_file = Path(hash_file)
        self.hash_file = hash_file
        self.file_hashes = self.load()

    def load(self):
        if self.hash_file.exists():
            try:
                with open(self.hash_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading file hashes: {e}")
                return {}
        return {}
    
    def save(self, hashes):
        try:
            with open(self.hash_file, "w", encoding="utf-8") as f:
                json.dump(hashes, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving file hashes: {e}")

    def update(self, file):
        try:
            self.file_hashes[file] = Path(file).stat().st_mtime
        except Exception as e:
            logger.error(f"Error updating file hash for {file}: {e}")

class ChromaIndexer:
    def __init__(self, collection, lock, text_splitter, hash_manager):
        self.collection = collection
        self.lock = lock
        self.text_splitter = text_splitter
        self.hash_manager = hash_manager

    def index_files(self, files):
        files_to_process = self._get_files_to_process(files)
        files_indexed = []
        errors = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_file = {
                executor.submit(self._process_file, file):file
                for file in files_to_process
            }
            for future in as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    if future.result():
                        files_indexed.append(file)
                        self.hash_manager.update(file)
                except Exception as e:
                    errors.append(f"Error processing file {file}: {e}")
                    for f in future_to_file:
                        if not f.done():
                            f.cancel()
                    break
        if files_indexed:
            self.hash_manager.save(self.hash_manager.file_hashes)
        return files_indexed, errors

    def remove_files(self, files):
        files_removed = []
        file_hashes = self.hash_manager.file_hashes
        for file in files:
            norm_file = str(Path(file).resolve())
            try:
                with self.lock:
                    self.collection.delete(where={"source": norm_file})
                    files_removed = True
                if norm_file in file_hashes:
                    del file_hashes[norm_file]
                    files_removed.append(norm_file)
            except Exception as e:
                logger.error(f"Error removing docs from chroma: {e}")
        if files_removed:
            self.hash_manager.save(file_hashes)
        return files_removed

    def clear(self):
        try:
            with self.lock:
                self.collection.delete()
                self.hash_manager.file_hashes = {}
                self.hash_manager.save(self.hash_manager.file_hashes)
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")

    def _get_files_to_process(self, files):
        files_to_process = []
        for file in files:
            norm_file = str(Path(file).resolve())
            file_stat = Path(norm_file).stat()
            file_mtime = file_stat.st_mtime
            file_hashes = self.hash_manager.file_hashes
            if norm_file in file_hashes and file_hashes[norm_file] == file_mtime:
                continue
            files_to_process.append(norm_file)
        return files_to_process

    def _process_file(self, file):
        chunks = self.text_splitter.split(file)
        norm_file = str(Path(file).resolve())
        for chunk_index, chunk in enumerate(chunks):
            if chunk.strip():
                self._add_chunk(chunk, norm_file, chunk_index)
        return True

    def _add_chunk(self, chunk, source, chunk_index):
        chunk_id = self._generate_md5_hash(chunk, source)
        # match rule_id: ## **(numbers).(numbers)(spaces)(rule_id).
        # rule_id: (3 or more uppercase letters)(digits)-C(optional PP)
        rule_id_match = re.search(
                r'## \*\*\d+\.\d+\s+([A-Z]{3,}\d+-C(?:PP)?)\.',
                chunk[:2000]
            )
        with self.lock:
            existing = self.collection.get(ids=[chunk_id], include=["metadatas"])
            # skip if chunk already exists, but ensure rule_id is set if chunk matches
            if existing and existing.get("ids"):
                if not rule_id_match:
                    return
                existing_meta = existing.get("metadatas")
                if existing_meta and existing_meta[0].get("rule_id") != rule_id_match.group(1):
                    new_meta = {
                        **existing_meta,
                        "source": source,
                        "chunk_index": chunk_index,
                        "rule_id": rule_id_match.group(1)
                        }
                    self.collection.update(documents=[chunk], metadatas=[new_meta], ids=[chunk_id])
                return
            meta = {"source": source, "chunk_index": chunk_index}
            if rule_id_match:
                meta["rule_id"] = rule_id_match.group(1)
            self.collection.add(documents=[chunk], metadatas=[meta], ids=[chunk_id])
    
    @staticmethod
    def _generate_md5_hash(text, source):
        data = f"{source}:{text}"
        return hashlib.md5(data.encode('utf-8')).hexdigest()

class TextSplitter:
    CHUNK_SIZE_DEFAULT = 2000
    CHUNK_OVERLAP_DEFAULT = 200
    def __init__(self,
        chunk_size: int = CHUNK_SIZE_DEFAULT,
        chunk_overlap: int = CHUNK_OVERLAP_DEFAULT
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def split(self, file):
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
        """
        Splits text on chapter-level headers (##), preserving semantic boundaries.
        Then further splits each section if it exceeds chunk_size.
        """
        # match chapter-level headers: starts with ##(spaces)**(numbers)(space)
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

class ChromaRetriever:
    def __init__(self, collection):
        self.collection = collection
            
    def get_context(self, results):
        if not results:
            return ""
        context_chunks = []
        for i, result in enumerate(results, 1):
            source = result["metadata"].get("source", "unknown")
            content = result["content"]
            context_chunks.append(f"[source {i}: {source}]\n{content}")
        return "\n\n".join(context_chunks)

    def get_query_results(self, message, n_results):
        retrieved = []
        seen_ids = set()
        self._get_rule_results(message, seen_ids, retrieved)
        results = self.collection.query(
            query_texts=[message],
            n_results=n_results * 2,
            include=["documents", "metadatas", "distances"]
        )
        if not results["documents"] or not results["documents"][0]:
            return []
        result_ids = []
        if results.get("ids"):
            result_ids = results["ids"][0]
        for i, doc in enumerate(results["documents"][0]):
            if len(retrieved) >= n_results:
                break
            if result_ids and i < len(result_ids):
                doc_id = result_ids[i]
                if doc_id in seen_ids:
                    continue
                seen_ids.add(doc_id)
            retrieved.append({
                "content": doc,
                "metadata": self._get_metadata(results, i),
                "distance": self._get_distance(results, i)
                })
        return retrieved[:n_results]

    def _get_rule_results(self, message, seen_ids, retrieved):
        rule_id_match = re.search(r'([A-Z]{3,}\d+-C(?:PP)?)', message.upper())
        if not rule_id_match:
            return
        rule_id = rule_id_match.group(1)
        rule_results = self.collection.get(
            where={"rule_id": rule_id},
            include=["documents", "metadatas"]
        )
        if not rule_results["ids"]:
            return
        for idx, doc_id in enumerate(rule_results["ids"]):
            seen_ids.add(doc_id)
            doc = rule_results["documents"][idx]
            meta = rule_results["metadatas"][idx] if rule_results["metadatas"] else {}
            retrieved.append({
                "content": doc,
                "metadata": meta,
                "distance": 0.0
            })

    @staticmethod
    def _get_metadata(results, i):
        if not results["metadatas"] or not results["metadatas"][0]:
            return {}
        if i >= len(results["metadatas"][0]):
            return {}
        return results["metadatas"][0][i]
    
    @staticmethod
    def _get_distance(results, i):
        if not results["distances"] or not results["distances"][0]:
            return None
        if i >= len(results["distances"][0]):
            return None
        return results["distances"][0][i]
