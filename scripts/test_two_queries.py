"""
Run two specific queries through full pipeline (retrieval + LLM) and print context and reply.

Use to verify both that the right chunks are retrieved and that the final answer is correct.

  python -m scripts.test_two_queries

Requires GEMINI_API_KEY in .env. Uses same RagClient and generate_response as the app.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chatbot import generate_response, rag_client

QUESTIONS = [
    "Give me implementation detail for PRE30-C",
    "What are common examples of vulnerability in LLM?",
]

CONTEXT_PREVIEW_CHARS = 2500


def main():
    n = int(os.getenv("N_RESULTS", "50"))
    print("N_RESULTS =", n)
    print()
    for i, q in enumerate(QUESTIONS, 1):
        print("=" * 72)
        print(f"Question {i}: {q}")
        print("-" * 72)
        context = rag_client.get_context(q, n_results=n)
        preview = context[:CONTEXT_PREVIEW_CHARS] if context else "(no context)"
        if len(context or "") > CONTEXT_PREVIEW_CHARS:
            preview += "\n... [truncated]"
        print("Context preview (first ~2500 chars):")
        print(preview)
        print("-" * 72)
        print("Generating reply...")
        reply = generate_response(q, context)
        print("Reply:")
        print(reply)
        print()


if __name__ == "__main__":
    main()
