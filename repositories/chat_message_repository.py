
from datetime import datetime
from db.schemas.ChatMessage import ChatMessage
from db.schemas.ChatSession import ChatSession
from sqlalchemy.orm import Session
from dto.message.message import CreateMessage
from errors.user import SessionNotFound


def create_message_db(data: CreateMessage, session_id: int, userId: int, db: Session):

    try:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id).first()
        if not session:
            raise SessionNotFound()

        message = ChatMessage(
            text=data.content,
            created_at=datetime.now(),
            role=data.role,
            created_by=userId,
            session_id=session_id
        )

        return message
    except Exception as e:
        raise e
