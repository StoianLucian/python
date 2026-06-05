
from datetime import datetime
from db.schemas.ChatMessage import ChatMessage
from db.schemas.ChatSession import ChatSession
from db.schemas.Image import Image
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


def create_image_message_db(images: list[str], message_id: str, db: Session):
    try:
        image_objects = [
            Image(text=image, message_id=message_id)
            for image in images
        ]

        db.add_all(image_objects)
        db.commit()
        
        print("image saved -----------------")

        return image_objects
    except Exception:
        db.rollback()
        raise
