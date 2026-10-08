
from datetime import datetime
from db.schemas.chat_message import ChatMessage
from db.schemas.chat_session import ChatSession
from db.schemas.image import Image
from sqlalchemy.orm import Session
from dto.message.message import CreateMessage
from repositories.chat_session_repository import check_session_exists


def create_message_db(data: CreateMessage, session_id: int, userId: int, db: Session):

    try:
        check_session_exists(session_id, db)

        message = ChatMessage(
            text=data.content,
            created_at=datetime.now(),
            role=data.role,
            created_by=userId,
            session_id=session_id
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        return message
    except Exception:
        db.rollback()
        raise


def get_recent_messages(session_id: int, created_by, limit: int, db: Session):
    """Return the most recent `limit` messages of one conversation, oldest-first.

    Scoped to the owning user when `created_by` is provided, so one user can
    never recall another's conversation. Fetched newest-first with a LIMIT (so
    long conversations don't load entirely) then reversed to chronological order.
    """
    query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
    if created_by is not None:
        query = query.filter(ChatMessage.created_by == created_by)

    rows = query.order_by(ChatMessage.id.desc()).limit(limit).all()
    return list(reversed(rows))


def create_image_message_db(images: list[str], message_id: str, db: Session):
    try:
        image_objects = [
            Image(text=image, message_id=message_id)
            for image in images
        ]

        db.add_all(image_objects)
        db.commit()

        return image_objects
    except Exception:
        db.rollback()
        raise
