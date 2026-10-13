"""conversation summary chunks: scope chunks to a session + source_type,
track summary high-water mark on chat_sessions

Revision ID: e3a4b5c6d7f8
Revises: d2f3a4b5c6e7
Create Date: 2026-10-12 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3a4b5c6d7f8'
down_revision: Union[str, Sequence[str], None] = 'd2f3a4b5c6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Let conversation-summary chunks live in the same table as document chunks
    # but be queried apart. `source_type` separates the two pools so document
    # search can stay documents-only; `session_id` scopes a summary chunk to its
    # conversation for same-session recall.
    op.add_column(
        "chunks",
        sa.Column("source_type", sa.String(), nullable=False,
                  server_default="document"),
    )
    op.alter_column("chunks", "source_type", server_default=None)
    op.add_column("chunks", sa.Column("session_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_chunks_session_id",
        "chunks", "chat_sessions",
        ["session_id"], ["id"],
    )
    # Partial index to make the session-scoped summary lookup cheap.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunks_session_summary "
        "ON chunks (session_id) WHERE source_type = 'conversation_summary'"
    )

    # Document chunks always have these; conversation-summary chunks don't, so
    # relax them to nullable.
    op.alter_column("chunks", "document_id", nullable=True)
    op.alter_column("chunks", "page_number", nullable=True)

    # High-water mark: the id of the last message the stored summary covers, so
    # we can summarize incrementally and gate on how many new messages exist.
    op.add_column(
        "chat_sessions",
        sa.Column("summary_last_message_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("chat_sessions", "summary_last_message_id")
    op.alter_column("chunks", "page_number", nullable=False)
    op.alter_column("chunks", "document_id", nullable=False)
    op.execute("DROP INDEX IF EXISTS ix_chunks_session_summary")
    op.drop_constraint("fk_chunks_session_id", "chunks", type_="foreignkey")
    op.drop_column("chunks", "session_id")
    op.drop_column("chunks", "source_type")
