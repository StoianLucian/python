"""create documents table

Revision ID: 5dd3d8a69416
Revises: 
Create Date: 2026-02-17 10:46:55.356456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '5dd3d8a69416'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
    )

    op.execute("""
        CREATE INDEX documents_embedding_idx
        ON documents
        USING ivfflat (embedding vector_cosine_ops)
    """)


def downgrade() -> None:
    op.drop_table("documents")
    op.execute("DROP EXTENSION IF EXISTS vector")
