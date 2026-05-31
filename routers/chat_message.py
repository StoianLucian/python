from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload
from db.connection import get_db
from db.schemas.ChatSession import ChatSession
from dto.message.message import CreateMessage
from repositories import login_user_db, logout_user_db
from errors.user import SessionNotFound

from repositories.aiChat_repository import initialize_model_generate, return_smallest_model
from repositories.auth_repository import LoginRequest, check_token
from repositories.chat_message_repository import create_message_db
from repositories.chat_session_repository import check_session_exists

router = APIRouter(prefix="/message", tags=["chat messages"])


@router.post("/{session_id}")
def create_session(session_id: int, data: CreateMessage, db: Session = Depends(get_db), user=Depends(check_token)):
    try:
        check_session_exists(session_id, db)

        message = create_message_db(data, session_id, user["user_id"], db)

        db.add(message)
        db.commit()
        db.refresh(message)

        return {"success": True, "message_id": message.id}

    except Exception as e:
        db.rollback()
        raise e()
