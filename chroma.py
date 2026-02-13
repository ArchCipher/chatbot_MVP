import os
import hashlib
import chromadb
from chromadb.utils import embedding_functions


class RAGClient:
    """RAG client using ChromaDB with sentence-transformers embeddings."""

    def __init__(self, persist_dir: str = "./chroma_db", knowledge_base_dir: str = "./knowledge_base"):
        self.persist_dir = persist_dir
        self.knowledge_base_dir = knowledge_base_dir

        self.client = chromadb.PersistentClient(path=persist_dir)

        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            embedding_function=self.embedding_fn
        )

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
        """Split text into overlapping chunks for better retrieval."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start = end - overlap
        return chunks

    def _generate_id(self, text: str, source: str) -> str:
        """Generate a unique ID for a document chunk."""
        content = f"{source}:{text}"
        return hashlib.md5(content.encode()).hexdigest()

    def load_knowledge_base(self):
        """Load and vectorize all documents from the knowledge base directory."""
        if not os.path.exists(self.knowledge_base_dir):
            return

        documents = []
        ids = []
        metadatas = []

        for filename in os.listdir(self.knowledge_base_dir):
            filepath = os.path.join(self.knowledge_base_dir, filename)
            if not os.path.isfile(filepath):
                continue

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            chunks = self._chunk_text(content)
            for i, chunk in enumerate(chunks):
                doc_id = self._generate_id(chunk, filename)
                # Skip if already exists
                existing = self.collection.get(ids=[doc_id])
                if existing["ids"]:
                    continue

                documents.append(chunk)
                ids.append(doc_id)
                metadatas.append({
                    "source": filename,
                    "chunk_index": i
                })

        if documents:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            print(f"Added {len(documents)} chunks to the knowledge base")

    def query(self, query_text: str, n_results: int = 3) -> list[dict]:
        """Query the knowledge base and return relevant documents with metadata."""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        retrieved = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                retrieved.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None
                })
        return retrieved

    def get_context_string(self, query_text: str, n_results: int = 3) -> str:
        """Get formatted context string for LLM prompt."""
        results = self.query(query_text, n_results)
        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results, 1):
            source = result["metadata"].get("source", "unknown")
            content = result["content"]
            context_parts.append(f"[Source {i}: {source}]\n{content}")

        return "\n\n".join(context_parts)
