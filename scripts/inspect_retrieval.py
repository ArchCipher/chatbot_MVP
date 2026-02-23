"""
Print exact retrieved chunks (and sources) for a fixed list of questions.

Use this to verify retrieval returns content from your DB (source_docs), not from the web.
No LLM call—only ChromaDB retrieval. Run from project root:

  python -m scripts.inspect_retrieval              # writes to inspect_retrieval_output.txt
  python -m scripts.inspect_retrieval --stdout      # print to console

Uses COLLECTION_NAME, PERSISTENT_STORAGE, COLLECTION_PATH, N_RESULTS from .env.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from chroma import RagClient

N_RESULTS = int(os.getenv("N_RESULTS", "50"))

QUESTIONS = [
    "How many documents do you have in your database?",
    "give me a concise summary of sei C coding standard in 5 lines within 50 words",
    "give me a concise summary of sei C++ coding standard in 5 lines within 50 words",
    "Give me 5 rules of sei C++ coding standard that i should follow for safe coding",
    "Give me 5 rules of sei C coding standard that i should follow for safe coding",
    "Give me 5 C coding standard that i should follow",
    "What is PRE30-C?",
    "What is DCL30-C?",
    "Explain EXP34-C",
    "What is STR31-C?",
    "What does MEM30-C say?",
    "List OWASP Top 10 web application security risks",
    "What is SQL injection and how do I prevent it?",
]


def format_source(meta):
    """Short source label from metadata (path basename or rule_id)."""
    source = meta.get("source", "unknown")
    if isinstance(source, str) and "/" in source:
        source = os.path.basename(source)
    rule_id = meta.get("rule_id")
    if rule_id:
        return f"{source} (rule_id={rule_id})"
    return source


def run(stdout=False):
    rag = RagClient(
        name=os.getenv("COLLECTION_NAME", "my-collection"),
        persistent_storage=os.getenv("PERSISTENT_STORAGE", "chroma_db"),
        collection_path=os.getenv("COLLECTION_PATH", "source_docs"),
    )
    n = N_RESULTS
    out = []
    out.append(f"Retrieval inspection (n_results={n})")
    out.append("Sources and content are from ChromaDB only (your indexed docs).")
    out.append("")
    for i, q in enumerate(QUESTIONS, 1):
        results = rag.retriever.get_query_results(q, n_results=n)
        out.append("=" * 72)
        out.append(f"Question {i}: {q}")
        out.append(f"Chunks retrieved: {len(results)}")
        out.append("-" * 72)
        for j, r in enumerate(results, 1):
            dist = r.get("distance")
            dist_str = f" distance={dist:.4f}" if dist is not None else ""
            src = format_source(r.get("metadata") or {})
            out.append(f"[{j}] source: {src}{dist_str}")
            out.append(r.get("content", "")[:2000])
            if len(r.get("content", "")) > 2000:
                out.append("... [truncated]")
            out.append("")
        out.append("")
    text = "\n".join(out)
    if stdout:
        print(text)
    else:
        path = os.path.join(os.path.dirname(__file__), "..", "inspect_retrieval_output.txt")
        path = os.path.abspath(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Written to {path}")


if __name__ == "__main__":
    run(stdout="--stdout" in sys.argv)
