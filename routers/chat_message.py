from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.connection import get_db
from dto.message.message import CreateMessage

from repositories.auth_repository import LoginRequest, check_token
from repositories.chat_message_repository import create_image_message_db, create_message_db
from repositories.chat_session_repository import check_session_exists

router = APIRouter(prefix="/message", tags=["chat messages"])


@router.post("/{session_id}")
def create_message(session_id: int, data: CreateMessage, db: Session = Depends(get_db), user=Depends(check_token)):
    try:
        check_session_exists(session_id, db)

        message = create_message_db(data, session_id, user["user_id"], db)

        if data.images:
            create_image_message_db(data.images, message.id, db)

        return {"success": True, "message_id": message.id}

    except Exception as e:
        db.rollback()
        raise e()
