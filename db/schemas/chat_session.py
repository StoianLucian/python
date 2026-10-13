from typing import List, Optional
from datetime import datetime

from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.schemas.base import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    title: Mapped[str] = mapped_column(String, nullable=False)

    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Id of the last chat message the stored summary covers. Lets us summarize
    # incrementally (only the new tail) and gate on how many new messages exist.
    summary_last_message_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(Date, nullable=False)
    
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)

    chat_messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        order_by="ChatMessage.id",
        cascade="all, delete-orphan"
    )
