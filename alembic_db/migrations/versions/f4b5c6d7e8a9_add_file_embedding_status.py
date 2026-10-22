"""add background-embedding status/progress columns to files

Revision ID: f4b5c6d7e8a9
Revises: e3a4b5c6d7f8
Create Date: 2026-10-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4b5c6d7e8a9'
down_revision: Union[str, Sequence[str], None] = 'e3a4b5c6d7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Uploads now return immediately and embed in a background task; these track
    # that work so the UI can poll it. Existing rows predate background embedding
    # and already have their chunks, so backfill them as "done".
    op.add_column(
        "files",
        sa.Column("status", sa.String(), nullable=False,
                  server_default="pending"),
    )
    op.add_column(
        "files",
        sa.Column("chunks_done", sa.Integer(), nullable=False,
                  server_default="0"),
    )
    op.add_column(
        "files",
        sa.Column("chunks_total", sa.Integer(), nullable=False,
                  server_default="0"),
    )
    op.add_column("files", sa.Column("error", sa.String(), nullable=True))

    op.execute("UPDATE files SET status = 'done'")

    # Drop the server defaults now that existing rows are populated; the app sets
    # these explicitly on insert.
    op.alter_column("files", "status", server_default=None)
    op.alter_column("files", "chunks_done", server_default=None)
    op.alter_column("files", "chunks_total", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("files", "error")
    op.drop_column("files", "chunks_total")
    op.drop_column("files", "chunks_done")
    op.drop_column("files", "status")
