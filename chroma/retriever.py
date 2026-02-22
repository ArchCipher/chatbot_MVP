"""ChromaDB retrieval: semantic search plus rule-id boost for CERT-style queries."""

import re


class ChromaRetriever:
    """Retrieves chunks by semantic similarity, prepends rule chunk when message matches rule id."""

    def __init__(self, collection):
        self.collection = collection

    def get_context(self, results) -> str:
        """Format list of {content, metadata} into a single context string with source labels."""
        if not results:
            return ""
        context_chunks = []
        for i, result in enumerate(results, 1):
            source = result["metadata"].get("source", "unknown")
            content = result["content"]
            context_chunks.append(f"[source {i}: {source}]\n{content}")
        return "\n\n".join(context_chunks)

    def get_query_results(self, message, n_results):
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
            retrieved.append(
                {
                    "content": doc,
                    "metadata": self._get_metadata(results, i),
                    "distance": self._get_distance(results, i),
                }
            )
        return retrieved[:n_results]

    def _get_rule_results(self, message, seen_ids, retrieved):
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
    def _get_metadata(results, i):
        """Get metadata for i-th document in Chroma query result."""
        if not results["metadatas"] or not results["metadatas"][0]:
            return {}
        if i >= len(results["metadatas"][0]):
            return {}
        return results["metadatas"][0][i]

    @staticmethod
    def _get_distance(results, i):
        """Get distance for i-th document in Chroma query result."""
        if not results["distances"] or not results["distances"][0]:
            return None
        if i >= len(results["distances"][0]):
            return None
        return results["distances"][0][i]
