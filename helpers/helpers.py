import re

from db.connection import SessionLocal
from fastapi import HTTPException
from enum import Enum

from sqlalchemy import select, text

from db.schemas.chunk import Chunk
from repositories.ai_chat_repository import get_embedding, return_available_embedding_models
from services.reranker import rerank
import os


def raise_error(status: int, message: str, code: Enum):
    raise HTTPException(
        status_code=status,
        detail={
            "message": message,
            "code": code.value
        }
    )


def return_document_context(context: str, created_by: int):
    db = SessionLocal()

    try:

        embedding_models = return_available_embedding_models()
        embedding = get_embedding(
            text=context, model=embedding_models[0]["name"], task="query")

        # Over-retrieve by embedding distance, then let the reranker grade which
        # candidates are actually relevant (and in what order). Vector distance
        # alone always returns k rows even when none are on-topic.
        # Scoped to the requesting user so search never surfaces another user's
        # documents.
        stmt = (
            select(Chunk.document_id, Chunk.content, Chunk.page_number)
            .where(Chunk.source_type == "document")
            .where(Chunk.created_by == created_by)
            .order_by(Chunk.embedding.op("<=>")(embedding))
            .limit(20)
        )

        # HNSW is approximate and our created_by/source_type filters run as a
        # post-filter, which can drop true-nearest rows. Tell pgvector (>=0.8)
        # to keep scanning the index until LIMIT rows survive the filter.
        # relaxed_order (not strict) is fine: we rerank right after, so exact
        # distance order out of the DB doesn't matter. SET LOCAL scopes these
        # to this transaction so pooled connections aren't affected.
        db.execute(text("SET LOCAL hnsw.iterative_scan = relaxed_order"))
        db.execute(text("SET LOCAL hnsw.ef_search = 100"))

        results = db.execute(stmt).all()
        
        print("sesults =====", context, results)

        candidates = [
            {"source_id": source_id, "content": content, "page_number": page_number}
            for source_id, content, page_number in results
        ]

        # Reranks by LLM-graded relevance and drops off-topic chunks; returns the
        # relevant few (empty when nothing clears the threshold, so the caller can
        # tell the knowledge base has no answer).
        return rerank(context, candidates, top_k=5)
    except Exception as e:
        return e

    finally:
        db.close()


def split_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def sanitize_input(text):
    page_text = text.replace("\n", " ")
    page_text = re.sub(r"\s+", " ", page_text).strip()
    return page_text
