from datetime import datetime
from db.schemas import ChatMessage
from db.schemas.chat_session import ChatSession
from db.schemas.chunk import Chunk
from sqlalchemy.orm import Session, selectinload
from errors.user import SessionNotFound
from repositories.ai_chat_repository import (
    get_embedding,
    initialize_model_generate,
    return_available_embedding_models,
    return_smallest_model,
    session_summary_options,
)
from prompts.prompts import conversation_summary_prompt, session_summary_prompt


# Minimum number of new (un-summarized) messages before we regenerate the
# summary. Gates the model + embedding calls so a per-turn client call is cheap:
# below the threshold we return the existing summary untouched. Each regenerate
# re-embeds and re-indexes the summary chunk, so we don't want to do it per turn.
SUMMARY_MIN_NEW_MESSAGES = 5

# Marks a chunk as a conversation's rolling summary (vs an indexed "document"),
# so summary chunks and document chunks stay in separate retrieval pools.
CONVERSATION_SUMMARY_SOURCE = "conversation_summary"


def create_session_summary(prompt: str):

    final_prompt = session_summary_prompt.format(
        user_prompt=prompt)

    model = return_smallest_model()

    session_summary = initialize_model_generate(
        model, final_prompt, False, session_summary_options)

    response = session_summary.get('response')

    if not response:
        return "error"

    return response


def generate_conversation_summary(conversation: str, previous_summary=None):
    """Produce an updated rolling summary from the previous summary + the new
    messages (not a title, and not a from-scratch re-summary of everything).

    Feeding the prior summary in keeps earlier important points alive as the
    chat grows, instead of compressing the whole transcript harder each time.
    Uses the smallest model with the same deterministic options as the title
    generator. Returns None if the model gives nothing back."""
    final_prompt = conversation_summary_prompt.format(
        previous_summary=previous_summary or "(none)",
        conversation=conversation,
    )

    model = return_smallest_model()

    result = initialize_model_generate(
        model, final_prompt, False, session_summary_options)

    return result.get("response")


def upsert_summary_chunk(session_id: int, created_by: int, summary: str, db: Session):
    """Embed `summary` and store it as this session's single conversation-summary
    chunk, so same-session RAG retrieval can find it. Replaces any prior summary
    chunk for the session (one chunk per session, no duplicates/churn)."""
    embedding_models = return_available_embedding_models()
    embedding = get_embedding(text=summary, model=embedding_models[0]["name"])

    db.query(Chunk).filter(
        Chunk.session_id == session_id,
        Chunk.source_type == CONVERSATION_SUMMARY_SOURCE,
    ).delete(synchronize_session=False)

    db.add(Chunk(
        source_type=CONVERSATION_SUMMARY_SOURCE,
        session_id=session_id,
        content=summary,
        embedding=embedding,
        created_by=created_by,
        created_at=datetime.now(),
    ))


def summarize_session(session_id: int, db: Session, force: bool = False):
    """Update a session's rolling summary from its stored messages, persist it on
    the session, and (re)embed it as a conversation-summary chunk for RAG.

    Reads the already-saved messages from the DB (the frontend persists both the
    user turn and the AI response before calling this), so the summary always
    reflects the complete, final conversation. Runs from its own endpoint,
    separate from the chat stream, so summarizing never slows down the chat.

    Incremental + gated: only the messages newer than `summary_last_message_id`
    are summarized (folded into the previous summary), and we skip the model +
    embedding work entirely unless at least SUMMARY_MIN_NEW_MESSAGES new messages
    have accumulated — unless `force` is set. Returns the current summary (new or
    existing), or None if there's nothing to summarize yet."""
    check_session_exists(session_id, db)

    session = db.query(ChatSession).filter(
        ChatSession.id == session_id
    ).first()

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id)
        .all()
    )
    if not messages:
        return session.summary

    covered_id = session.summary_last_message_id or 0
    new_messages = [m for m in messages if m.id > covered_id and m.text]

    # Not enough new content to be worth a (re-embedding) regenerate — leave the
    # stored summary as-is. `force` bypasses the gate (e.g. an explicit refresh).
    if not force and len(new_messages) < SUMMARY_MIN_NEW_MESSAGES:
        return session.summary

    new_tail = "\n".join(f"{m.role}: {m.text}" for m in new_messages)
    if not new_tail.strip():
        return session.summary

    summary = generate_conversation_summary(
        new_tail, previous_summary=session.summary)
    if not summary:
        return session.summary

    session.summary = summary
    session.summary_last_message_id = messages[-1].id
    upsert_summary_chunk(session_id, session.created_by, summary, db)
    db.commit()

    return summary


def conversation_context_for(session_id: int, db: Session, max_recent: int = 10,
                             max_chars: int = 4000) -> str:
    """Build the conversation context to feed the agents WITHOUT resending the
    whole history: the rolling summary (covers everything up to
    `summary_last_message_id`) plus the handful of newer messages not yet folded
    into it. Returns a bounded "role: text" block, or "" when there's nothing."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session is None:
        return ""

    parts = []
    if session.summary:
        parts.append("Summary of earlier conversation:\n" + session.summary)

    covered_id = session.summary_last_message_id or 0
    recent = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session_id,
            ChatMessage.id > covered_id,
            ChatMessage.text.isnot(None),
        )
        .order_by(ChatMessage.id)
        .all()
    )
    recent = recent[-max_recent:]
    if recent:
        lines = "\n".join(f"{m.role}: {m.text}" for m in recent)
        parts.append("Recent messages:\n" + lines)

    context = "\n\n".join(parts)
    return context[:max_chars]


def get_user_session_by_id(session_id, db: Session):

    try:

        check_session_exists(session_id, db)

        session = (
            db.query(ChatSession)
            .options(
                selectinload(ChatSession.chat_messages)
                .selectinload(ChatMessage.images)
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


def delete_session_db(session_id: int, db: Session):
    try:

        check_session_exists(session_id, db)

        session = db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).first()

        # Remove the session's conversation-summary chunk(s) first — they carry a
        # FK to chat_sessions (fk_chunks_session_id) with no cascade, so deleting
        # the session while they exist raises a ForeignKeyViolation.
        db.query(Chunk).filter(
            Chunk.session_id == session_id
        ).delete(synchronize_session=False)

        db.delete(session)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e


def check_session_exists(session_id: int, db: Session):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id).first()
    if not session:
        raise SessionNotFound()


def update_session_title_db(session_id: int, new_title: str, db: Session):
    try:

        check_session_exists(session_id, db)

        session = db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).first()

        if not session:
            raise SessionNotFound()

        session.title = new_title
        db.commit()
        db.refresh(session)

        return session

    except Exception as e:
        raise e
