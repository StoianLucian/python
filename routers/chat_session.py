from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload
from db.connection import get_db
from dto.session.session import CreateSession
from errors.chat import SummaryNotCreatedError
from errors.user import SessionNotFound

from repositories.auth_repository import LoginRequest, check_token
from repositories.chat_session_repository import create_session_db, create_session_summary, delete_session_db, get_user_session_by_id, get_user_sessions, session_summary_prompt

router = APIRouter(prefix="/session",
                   tags=["chat session"],
                   dependencies=[Depends(check_token)])


@router.post("/")
def create_session(data: CreateSession, db: Session = Depends(get_db), user=Depends(check_token)):
    try:
        query = data.query

        session_summary = create_session_summary(query)
        if not session_summary:
            raise SummaryNotCreatedError()

        session = create_session_db(session_summary, user["user_id"])
        db.add(session)
        db.commit()
        db.refresh(session)

        return session.id

    except Exception as e:
        db.rollback()
        raise e


@router.get("/")
def get_sessions(db=Depends(get_db), user=Depends(check_token)):
    try:
        return get_user_sessions(db, user["user_id"])
    except Exception as e:
        raise e


@router.get("/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db), user=Depends(check_token)):
    try:
        return get_user_session_by_id(session_id, db)
    except Exception as e:
        raise e


@router.delete("/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), user=Depends(check_token)):
    try:
        delete_session_db(session_id, db)

        return {"success": True, "message": "Session deleted successfully"}

    except Exception as e:
        db.rollback()
        raise e
