"""add cosine HNSW index on chunks.embedding

The document-search query in helpers.return_document_context orders candidate
chunks by cosine distance (pgvector `<=>`) but no index backed that column, so
every search did a full sequential scan over chunks. This adds an HNSW index
with the cosine opclass so the `<=>` ORDER BY ... LIMIT can use it.

HNSW (not IVFFlat) because it builds fine on an empty table and needs no
`lists` tuning / training pass.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_cosine "
        "ON chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_cosine")
