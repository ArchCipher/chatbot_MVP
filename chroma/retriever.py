"""ChromaDB retrieval: semantic search plus rule-id boost for CERT-style queries."""

import re
from typing import Any

# Chroma query result item: content, metadata, optional distance
RetrievalResult = dict[str, Any]


class ChromaRetriever:
    """Retrieves chunks by semantic similarity, prepends rule chunk when message matches rule id."""

    def __init__(self, collection: Any) -> None:
        self.collection = collection

    def get_context(self, results: list[RetrievalResult]) -> str:
        """Format list of {content, metadata} into a single context string with source labels."""
        if not results:
            return ""
        context_chunks = []
        for i, result in enumerate(results, 1):
            source = result["metadata"].get("source", "unknown")
            content = result["content"]
            context_chunks.append(f"[source {i}: {source}]\n{content}")
        return "\n\n".join(context_chunks)

    def get_query_results(self, message: str, n_results: int) -> list[RetrievalResult]:
        """
        Rule-id match first (if any), then semantic search.
        Dedupe and return up to n_results.
        """
        retrieved = []
        seen_ids = set()
        self._get_rule_results(message, seen_ids, retrieved)
        results = self.collection.query(
            query_texts=[message],
            n_results=n_results * 2,
            include=["documents", "metadatas", "distances"],
        )
        documents = results.get("documents")
        if not documents or not documents[0]:
            return retrieved
        ids = results["ids"][0] if results.get("ids") else []
        for i, doc in enumerate(documents[0]):
            if len(retrieved) >= n_results:
                break
            if ids and i < len(ids):
                doc_id = ids[i]
                if doc_id in seen_ids:
                    continue
                seen_ids.add(doc_id)
            retrieved.append(
                {
                    "content": doc,
                    "metadata": self._get_metadata(results, i),
                    "distance": self._get_distance(results, i),
                }
            )
        return retrieved[:n_results]

    def _get_rule_results(
        self, message: str, seen_ids: set[str], retrieved: list[RetrievalResult]
    ) -> None:
        """If message contains a CERT-style rule id, prepend that chunk and mark ids seen."""
        rule_id_match = re.search(r"([A-Z]{3,}\d+-C(?:PP)?)", message.upper())
        if not rule_id_match:
            return
        rule_id = rule_id_match.group(1)
        rule_results = self.collection.get(
            where={"rule_id": rule_id}, include=["documents", "metadatas"]
        )
        if not rule_results["ids"]:
            return
        for idx, doc_id in enumerate(rule_results["ids"]):
            seen_ids.add(doc_id)
            doc = rule_results["documents"][idx]
            meta = rule_results["metadatas"][idx] if rule_results["metadatas"] else {}
            retrieved.append({"content": doc, "metadata": meta, "distance": 0.0})

    @staticmethod
    def _get_metadata(results: dict[str, Any], i: int) -> dict[str, Any]:
        """Get metadata for i-th document in Chroma query result."""
        metadatas = results.get("metadatas")
        if not metadatas or not metadatas[0]:
            return {}
        if i >= len(metadatas[0]):
            return {}
        return metadatas[0][i]

    @staticmethod
    def _get_distance(results: dict[str, Any], i: int) -> float | None:
        """Get distance for i-th document in Chroma query result."""
        distances = results.get("distances")
        if not distances or not distances[0]:
            return None
        if i >= len(distances[0]):
            return None
        return distances[0][i]
