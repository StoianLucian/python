"""add chat_sessions.summary

Revision ID: d2f3a4b5c6e7
Revises: b1e2c3d4f5a6
Create Date: 2026-10-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2f3a4b5c6e7'
down_revision: Union[str, Sequence[str], None] = 'b1e2c3d4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Stores a running summary of the conversation. Nullable: existing sessions
    # have none, and it is only populated once a summary is generated.
    op.add_column(
        "chat_sessions",
        sa.Column("summary", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("chat_sessions", "summary")
