from datetime import datetime
from typing import List

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.schemas.Base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    text: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(Date, nullable=False)

    role: Mapped[str] = mapped_column(String, nullable=False)

    created_by: Mapped[int] = mapped_column(Integer, nullable=False)

    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id"),
        nullable=False
    )

    images: Mapped[List["Image"]] = relationship(
        "Image",
        order_by="Image.id",
        cascade="all, delete-orphan",
    )
