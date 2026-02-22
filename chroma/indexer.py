"""ChromaDB indexing: chunk documents, add/update/remove in collection, track file mtimes."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import logging
from pathlib import Path
import re

from chroma.models import CollectionResult

logger = logging.getLogger("ChromaIndexer")

class ChromaIndexer:
    """Indexes markdown files into a ChromaDB collection"""

    def __init__(self, collection, lock, text_splitter, hash_manager):
        self.collection = collection
        self.lock = lock
        self.text_splitter = text_splitter
        self.hash_manager = hash_manager

    def index_files(self, files):
        """Index only changed files (by mtime)"""
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
        return CollectionResult(files=files_indexed, errors=errors)

    def remove_files(self, files)->list[str]:
        """Delete chunks for given source paths from collection and hash file"""
        files_removed = []
        file_hashes = self.hash_manager.file_hashes
        for file in files:
            norm_file = str(Path(file).resolve())
            try:
                with self.lock:
                    # check if file exists in collection
                    result = self.collection.get(where={"source": norm_file})
                    if not result.get("ids"):
                        continue
                    # delete file from collection
                    self.collection.delete(where={"source": norm_file})
                    files_removed.append(norm_file)
                if norm_file in file_hashes:
                    del file_hashes[norm_file]
            except Exception as e:
                logger.error(f"Error removing docs from chroma: {e}")
        if files_removed:
            self.hash_manager.save(file_hashes)
        return files_removed

    def clear(self):
        """Delete all documents in collection and clear hash file."""
        try:
            with self.lock:
                self.collection.delete()
                self.hash_manager.file_hashes = {}
                self.hash_manager.save(self.hash_manager.file_hashes)
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")

    def _get_files_to_process(self, files):
        """Return list of files that are new or have mtime different from stored hash."""
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
        """Split file into chunks and add each to collection."""
        chunks = self.text_splitter.split(file)
        norm_file = str(Path(file).resolve())
        for chunk_index, chunk in enumerate(chunks):
            if chunk.strip():
                self._add_chunk(chunk, norm_file, chunk_index)
        return True

    def _add_chunk(self, chunk, source, chunk_index):
        """Add a chunk to collection"""
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
                    new_meta = {**existing_meta[0],
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
        """Generate chunk id from source path and content."""
        data = f"{source}:{text}"
        return hashlib.md5(data.encode('utf-8')).hexdigest()
