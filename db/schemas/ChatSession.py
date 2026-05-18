from typing import List
from datetime import datetime

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.schemas.Base import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    title: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(Date, nullable=False)

    chat_messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        order_by="ChatMessage.id",
        cascade="all, delete-orphan"
    )
