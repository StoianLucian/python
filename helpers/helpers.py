import re

from db.connection import SessionLocal
from fastapi import HTTPException
from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.schemas.chunk import Chunk
from repositories.ai_chat_repository import get_embedding, return_available_embedding_models
import os


def raise_error(status: int, message: str, code: Enum):
    raise HTTPException(
        status_code=status,
        detail={
            "message": message,
            "code": code.value
        }
    )


def return_context_2(context: str):
    db = SessionLocal()

    try:

        embedding_models = return_available_embedding_models()
        embedding = get_embedding(
            text=context, model=embedding_models[0]["name"])

        stmt = (
            select(Chunk.document_id, Chunk.content, Chunk.page_number)
            .where(Chunk.source_type == "document")
            .order_by(Chunk.embedding.op("<=>")(embedding))
            .limit(5)
        )

        results = db.execute(stmt).all()

        data = []

        for source_id, content, page_number in results:
            data.append({"source_id": source_id,
                        "content": content, "page_number": page_number})

        return data
    except Exception as e:
        return e

    finally:
        db.close()


def return_context(context: str, db: Session):
    embedding_models = return_available_embedding_models()
    embedding = get_embedding(
        text=context,
        model=embedding_models[0]["name"]
    )

    stmt = (
        select(Chunk.document_id, Chunk.content, Chunk.page_number)
        .where(Chunk.source_type == "document")
        .order_by(Chunk.embedding.op("<=>")(embedding))
        .limit(10)
    )

    results = db.execute(stmt).all()

    data = []

    for doc_id, content, page_number in results:
        data.append({"document_id": doc_id, "document_content": content,
                    "page_number": page_number})

    return data


def return_session_summary_context(query: str, session_id: int, db: Session):
    """Retrieve this session's conversation-summary chunk by vector similarity,
    scoped to the session so same-session recall never pulls in other sessions'
    summaries or document chunks. There's one summary chunk per session, so this
    returns at most one row; the vector order_by is kept for when that grows to
    several topical summary chunks per session."""
    embedding_models = return_available_embedding_models()
    embedding = get_embedding(text=query, model=embedding_models[0]["name"])

    stmt = (
        select(Chunk.content)
        .where(Chunk.source_type == "conversation_summary")
        .where(Chunk.session_id == session_id)
        .order_by(Chunk.embedding.op("<=>")(embedding))
        .limit(3)
    )

    return [content for (content,) in db.execute(stmt).all()]


def split_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def sanitize_input(text):
    page_text = text.replace("\n", " ")
    page_text = re.sub(r"\s+", " ", page_text).strip()
    return page_text
