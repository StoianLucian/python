"""LLM-as-reranker for RAG results.

Vector similarity (`<=>`) is a decent first-pass retriever but it returns the
top-k by embedding distance even when nothing is actually relevant. This module
takes those candidates and asks the configured chat model to grade each one's
relevance to the query on a 0-1 scale, then drops the low scorers and reorders
the rest. Reusing the existing provider keeps it $0 (Gemini/Ollama) with no
extra dependency.
"""

import json
import logging
import os

from lmm.factory import get_lmm_provider

logger = logging.getLogger(__name__)

# How relevant a passage must be (0-1) to survive. Tunable via env.
RERANK_THRESHOLD = float(os.getenv("RERANK_THRESHOLD", "0.5"))

_RERANK_SYSTEM = (
    "You are a relevance grader for a retrieval system. You are given a user "
    "query and several candidate passages. For EACH passage, judge how well it "
    "helps answer the query and assign a relevance score from 0.0 (irrelevant) "
    "to 1.0 (directly answers it). Judge only relevance to the query — not "
    "writing quality or length. Respond with ONLY a JSON object of the form "
    '{"scores": [{"index": <int>, "score": <float>}, ...]} with one entry per '
    "passage, using the given indices. Output no prose."
)


def _pick_model(provider) -> str:
    """Choose a light chat model for grading: an explicit RERANK_MODEL, else a
    'flash'/'mini'/'small'-class model when present, else the first available."""
    configured = os.getenv("RERANK_MODEL")
    if configured:
        return configured

    models = provider.list_models()
    if not models:
        raise RuntimeError("no chat model available for reranking")

    for marker in ("flash", "mini", "small", "haiku"):
        for m in models:
            if marker in m["id"].lower():
                return m["name"]
    return models[0]["name"]


def _response_text(response) -> str:
    """Extract text from a non-streaming chat response across providers
    (Gemini `.text`, Ollama `message.content`)."""
    text = getattr(response, "text", None)
    if text:
        return text
    message = getattr(response, "message", None)
    if message is not None:
        return getattr(message, "content", None) or ""
    if isinstance(response, dict):
        return (response.get("message") or {}).get("content") or ""
    return ""


def rerank(query: str, candidates: list[dict], *, content_key: str = "content",
           top_k: int = 5, threshold: float | None = None) -> list[dict]:
    """Return `candidates` reordered by LLM-graded relevance, keeping only those
    at/above `threshold` and at most `top_k`. On any failure (no model, bad JSON)
    the original candidates are returned unchanged so retrieval never breaks."""
    if not candidates:
        return []

    threshold = RERANK_THRESHOLD if threshold is None else threshold

    try:
        provider = get_lmm_provider()
        model = _pick_model(provider)

        passages = "\n\n".join(
            f"[{i}] {c.get(content_key, '')}" for i, c in enumerate(candidates)
        )
        messages = [
            {"role": "system", "content": _RERANK_SYSTEM},
            {"role": "user", "content": f"Query: {query}\n\nPassages:\n{passages}"},
        ]

        response = provider.chat(
            model=model, messages=messages, stream=False, format="json")
        payload = json.loads(_response_text(response))

        scores = {
            int(item["index"]): float(item["score"])
            for item in payload.get("scores", [])
            if "index" in item and "score" in item
        }
    except Exception:
        logger.exception("rerank failed; returning candidates unranked")
        return candidates[:top_k]

    scored = [
        (scores.get(i, 0.0), c)
        for i, c in enumerate(candidates)
    ]
    kept = [(s, c) for s, c in scored if s >= threshold]
    kept.sort(key=lambda pair: pair[0], reverse=True)

    return [c for _, c in kept[:top_k]]
