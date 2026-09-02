

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.schemas.base import Base


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    text: Mapped[str] = mapped_column(String, nullable=False)

    message_id: Mapped[int] = mapped_column(
        ForeignKey("chat_messages.id"),
        nullable=False
    )

    chat_message: Mapped["ChatMessage"] = relationship(
        "ChatMessage",
        back_populates="images"
    )
