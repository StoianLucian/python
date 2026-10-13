from typing import List, Optional
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.schemas.base import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # "document" (an indexed file) or "conversation_summary" (a session's rolling
    # summary). Keeps the two retrieval pools apart in one table.
    source_type: Mapped[str] = mapped_column(
        String, nullable=False, default="document")
    # Set only for document chunks.
    document_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Set only for conversation_summary chunks: the session they summarize.
    session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("chat_sessions.id"), nullable=True)
    content: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(Date, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(768))
