from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload
from db.connection import get_db
from errors.user import NotAuthenticatedError
from repositories import login_user_db, logout_user_db
from fastapi import Response
import logging
from db.schemas.ChatSession import ChatSession
from errors.user import SessionNotFound

from repositories.aiChat_repository import initialize_model_generate
from repositories.auth_repository import LoginRequest, check_token
from repositories.user_repository import get_user_by_id_db

router = APIRouter(prefix="/session", tags=["chat session"])


@router.post("/")
def create_session(db: Session = Depends(get_db)):

    try:
        session = ChatSession(
            title="some title",
            created_at=datetime.now()
        )

        db.add(session)
        db.commit()
        db.refresh(session)


    except Exception as e:
        db.rollback()
        raise SessionNotFound()


@router.get("/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)):
    try:
        session = (
            db.query(ChatSession)
            .options(
                selectinload(ChatSession.chat_messages)
            )
            .filter(ChatSession.id == session_id)
            .first()
        )

        if session is None:
            raise SessionNotFound()

        return session
    except Exception as e:
        raise SessionNotFound()
