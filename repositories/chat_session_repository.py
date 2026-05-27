from datetime import datetime
from db.schemas.ChatSession import ChatSession
from sqlalchemy.orm import Session, selectinload
from errors.user import SessionNotFound
from repositories.aiChat_repository import initialize_model_generate, return_smallest_model, session_summary_options, session_summary_prompt


def create_session_summary(prompt: str):

    final_prompt = session_summary_prompt.format(
        user_prompt=prompt)

    model = return_smallest_model()

    print("samllest", model)

    session_summary = initialize_model_generate(
        model, final_prompt, False, session_summary_options)

    response = session_summary.get('response')

    if not response:
        return "error"

    return response


def get_user_session_by_id(session_id, db: Session):

    try:
        session = (
            db.query(ChatSession)
            .options(
                selectinload(ChatSession.chat_messages)
            )
            .filter(ChatSession.id == session_id)
            .first()
        )

        return session
    except Exception as e:
        raise e


def get_user_sessions(db: Session, userId=int):
    try:
        sessions = (
            db.query(ChatSession)
            .filter(ChatSession.created_by == userId)
            .all()
        )

        return sessions
    except Exception as e:
        raise e


def create_session_db(title: str, userId: int):
    session = ChatSession(
        title=title,
        created_at=datetime.now(),
        created_by=userId,
    )

    return session

def check_session_exists(session_id: int, db: Session):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise SessionNotFound()
