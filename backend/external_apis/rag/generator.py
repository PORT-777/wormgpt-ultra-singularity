"""Build a grounded prompt from retrieved context."""
from __future__ import annotations


def build_prompt(question, results):
    context = "\n\n".join(f"[{i+1}] {r['text']}" for i, r in enumerate(results))
    return (f"Answer using only the numbered context. Cite sources by number.\n\n"
            f"Context:\n{context}\n\nQuestion: {question}")
