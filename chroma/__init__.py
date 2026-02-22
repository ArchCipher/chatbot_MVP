"""ChromaDB RAG package: indexing, retrieval, and file-hash tracking.

Public API: use RagClient to get_context, reload_collection, and list_files.
"""

from chroma.chroma import RagClient

__all__ = ["RagClient"]