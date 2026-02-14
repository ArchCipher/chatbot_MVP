'''
ChromaDB client
'''

import chromadb
import os
import hashlib
from langchain_text_splitters import RecursiveCharacterTextSplitter

class RagClient:
    def __init__(self):
        # in memory client:
        self.chroma_client = chromadb.Client()
        # for persistent data storage across restarts, use:
        # self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.chroma_client.get_or_create_collection("my-collection")

    @staticmethod
    def generate_md5_hash(text, source):
        data = f"{source}:{text}"
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    def add_docs_to_chroma(self, files):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(os.getenv("CHUNK_SIZE", 500)),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", 50))
        )
        files_indexed = []
        errors = []
        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                chunks = text_splitter.split_text(content)
                for i, chunk in enumerate(chunks):
                    if chunk.strip(): # skip empty chunks
                        doc_id = self.generate_md5_hash(chunk, file)
                        existing = self.collection.get(ids=[doc_id])
                        # skip if chunk already exists
                        if existing["ids"]:
                            continue
                        self.collection.add(
                            documents=[chunk], # handles tokenization, embedding, and indexing automatically
                            metadatas=[{"source": file, "chunk_index": i}],
                            ids=[doc_id]
                        )
                files_indexed.append(file)
            except FileNotFoundError:
                print(f"File not found: {file}")
                errors.append(f"File not found: {file}")
            except Exception as e:
                print(f"Error processing file {file}: {e}")
                errors.append(f"{file}: {e}")
        return files_indexed, errors

    def reload_collection(self):
        path = os.getenv("COLLECTION_PATH", "source_docs")
        if not os.path.exists(path):
            print(f"Collection path not found: {path}")
            return "Collection path not found"
        files = []
        for filename in os.listdir(path):
            filepath = os.path.join(path, filename)
            if not os.path.isfile(filepath):
                continue
            files.append(filepath)
        self.add_docs_to_chroma(files)
        return None

    @staticmethod
    def get_metadata(results, i):
        if not results["metadatas"] or not results["metadatas"][0]:
            return {}
        if i < len(results["metadatas"][0]):
            return results["metadatas"][0][i]
        return {}
    
    @staticmethod
    def get_distance(results, i):
        if not results["distances"] or not results["distances"][0]:
            return None
        if i < len(results["distances"][0]):
            return results["distances"][0][i]
        return None

    def get_query_results(self, message):
        # query chroma for context
        results = self.collection.query(
            query_texts=[message],
            n_results=int(os.getenv("N_RESULTS", 5)),
            include=["documents", "metadatas", "distances"]
        )
        retrieved = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                retrieved.append({
                    "content": doc,
                    "metadata": self.get_metadata(results, i),
                    "distance": self.get_distance(results, i)
                    })
        return retrieved

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