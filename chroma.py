'''
ChromaDB client
'''

import hashlib
import os
import re
from pathlib import Path

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pymupdf.layout
import pymupdf4llm

class RagClient:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path=os.getenv("PERSISTENT_STORAGE", "./chroma_db"))
        self.collection = self.chroma_client.get_or_create_collection("my-collection")
            
    def reload_collection(self):
        path_str = os.getenv("COLLECTION_PATH", "source_docs")
        path = Path(path_str)
        if not path.exists():
            print(f"Collection path not found: {path_str}")
            return "Collection path not found"
        files = []
        for filepath in path.iterdir():
            if not filepath.is_file():
                continue
            extension = filepath.suffix.lower()
            if extension == ".pdf":
                md_path = filepath.with_suffix(".md")
                if md_path.exists() and filepath.stat().st_mtime <= md_path.stat().st_mtime:
                    files.append(str(md_path.resolve()))
                else:
                    if self._extract_text_from_pdf(str(filepath.resolve())):
                        files.append(str(md_path.resolve()))
            elif extension == ".md":
                files.append(str(filepath.resolve()))
        files_indexed, errors = self.add_docs_to_chroma(files)
        if errors:
            return f"Completed with {len(errors)} error(s), {len(files_indexed)} files indexed"
        return None

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

    def add_docs_to_chroma(self, files):
        chunk_size = int(os.getenv("CHUNK_SIZE", 500))
        chunk_overlap = int(os.getenv("CHUNK_OVERLAP", 50))
        files_indexed = []
        errors = []
        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                chunks = self._split_on_markdown_headers(content, chunk_size, chunk_overlap)
                # normalise path to prevent duplicate entries
                norm_file = str(Path(file).resolve())
                for i, chunk in enumerate(chunks):
                    if chunk.strip(): # skip empty chunks
                        self.add_doc_to_chroma(chunk, norm_file, i)
                files_indexed.append(file)
            except FileNotFoundError:
                print(f"File not found: {file}")
                errors.append(f"File not found: {file}")
            except Exception as e:
                print(f"Error processing file {file}: {e}")
                errors.append(f"{file}: {e}")
        return files_indexed, errors

    def add_doc_to_chroma(self, chunk, norm_file, i):
        doc_id = self._generate_md5_hash(chunk, norm_file)
        existing = self.collection.get(ids=[doc_id], include=["metadatas"])
        # match rule_id: ## **(numbers).(numbers)(spaces)(rule_id).
        # rule_id: (3 or more uppercase letters)(digits)-C(optional PP)
        rule_id_match = re.search(
                r'## \*\*\d+\.\d+\s+([A-Z]{3,}\d+-C(?:PP)?)\.',
                chunk[:2000]
            )
        # skip if chunk already exists, but ensure rule_id is set if chunk matches
        if existing["ids"]:
            if rule_id_match:
                existing_meta = (existing.get("metadatas") or [{}])[0]
                if existing_meta.get("rule_id") != rule_id_match.group(1):
                    new_meta = {**existing_meta, "source": norm_file, "chunk_index": i, "rule_id": rule_id_match.group(1)}
                    self.collection.update(ids=[doc_id], documents=[chunk], metadatas=[new_meta])
            return
        meta = {"source": norm_file, "chunk_index": i}
        if rule_id_match:
            meta["rule_id"] = rule_id_match.group(1)
        self.collection.add(
            documents=[chunk],
            metadatas=[meta],
            ids=[doc_id]
        )

    @staticmethod
    def _split_on_markdown_headers(text, chunk_size, chunk_overlap):
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
            if match:
                # Start a new section if start of new chapter
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
        if current_section: # add last section
            sections.append('\n'.join(current_section))
        # If no headers found, return original text as single section
        if not sections:
            sections = [text]
        # Further split each section if it exceeds chunk_size
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        all_chunks = []
        for section in sections:
            section_chunks = text_splitter.split_text(section)
            all_chunks.extend(section_chunks)
        return all_chunks

    @staticmethod
    def _generate_md5_hash(text, source):
        data = f"{source}:{text}"
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    def get_context(self, message):
        results = self.get_query_results(message)
        if not results:
            return ""
        # build context
        context_chunks = []
        for i, result in enumerate(results, 1):
            source = result["metadata"].get("source", "unknown")
            content = result["content"]
            context_chunks.append(f"[source {i}: {source}]\n{content}")
        return "\n\n".join(context_chunks)

    def get_rule_results(self, rule_id, seen_ids, retrieved):
        rule_results = self.collection.get(
            where={"rule_id": rule_id},
            include=["documents", "metadatas"]
        )
        if rule_results["ids"]:
            for idx, doc_id in enumerate(rule_results["ids"]):
                seen_ids.add(doc_id)
                doc = rule_results["documents"][idx]
                meta = rule_results["metadatas"][idx] if rule_results["metadatas"] else {}
                retrieved.append({
                    "content": doc,
                    "metadata": meta,
                    "distance": 0.0
                })

    def get_query_results(self, message):
        n_results = int(os.getenv("N_RESULTS", 5))
        retrieved = []
        rule_id_match = re.search(r'([A-Z]{3,}\d+-C(?:PP)?)', message.upper())
        rule_id = rule_id_match.group(1) if rule_id_match else None
        seen_ids = set()
        if rule_id:
            try:
                self.get_rule_results(rule_id, seen_ids, retrieved)
            except Exception:
                pass
        results = self.collection.query(
            query_texts=[message],
            n_results=n_results * 2,
            include=["documents", "metadatas", "distances"]
        )
        if results["documents"] and results["documents"][0]:
            result_ids = results.get("ids", [[]])[0] if results.get("ids") else []
            for i, doc in enumerate(results["documents"][0]):
                doc_id = result_ids[i] if i < len(result_ids) else None
                if doc_id:
                    if doc_id in seen_ids:
                        continue
                    seen_ids.add(doc_id)
                if len(retrieved) >= n_results:
                    continue
                retrieved.append({
                    "content": doc,
                    "metadata": self._get_metadata(results, i),
                    "distance": self._get_distance(results, i)
                    })
            retrieved = retrieved[:n_results]
        return retrieved[:n_results]

    @staticmethod
    def _get_metadata(results, i):
        if not results["metadatas"] or not results["metadatas"][0]:
            return {}
        if i < len(results["metadatas"][0]):
            return results["metadatas"][0][i]
        return {}
    
    @staticmethod
    def _get_distance(results, i):
        if not results["distances"] or not results["distances"][0]:
            return None
        if i < len(results["distances"][0]):
            return results["distances"][0][i]
        return None