from typing import Optional

from fastmcp import FastMCP
from pydantic import BaseModel

from db.connection import SessionLocal
from import_folder.response import ToolResponse
from repositories.chat_message_repository import get_recent_messages


class HistoryTurn(BaseModel):
    role: str
    content: str


def register_conversation_history_tools(mcp: FastMCP):

    @mcp.tool
    async def get_conversation_history(
        limit: int = 20,
        session_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> ToolResponse[list[HistoryTurn]]:
        """
        Recall earlier messages from the CURRENT conversation.

        Use this when the user refers to something said earlier in this chat —
        e.g. "what did I ask before?", "the thing we talked about", "same as
        last time", or any follow-up that only makes sense with prior context —
        and that context is not already in front of you. Returns the most recent
        turns of this conversation (oldest-first) as {role, content}.

        Args:
            limit: How many of the most recent turns to return (default 20).
        """
        # `session_id` and `created_by` are injected server-side (never by the
        # model). Without a conversation to scope to, there is nothing to recall.
        if session_id is None:
            return ToolResponse(success=True, result=[])

        db = SessionLocal()
        try:
            rows = get_recent_messages(session_id, created_by, limit, db)
            turns = [{"role": m.role, "content": m.text} for m in rows]
            return ToolResponse(success=True, result=turns)
        except Exception as e:
            return ToolResponse(success=False, result=f"Error: {e}")
        finally:
            db.close()
