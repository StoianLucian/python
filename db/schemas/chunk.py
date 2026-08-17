from typing import List
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.schemas.base import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(Date, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(768))
