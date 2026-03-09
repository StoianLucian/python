"""create_files_tablee

Revision ID: b269babcdcd7
Revises: 1e1a58ec374d
Create Date: 2026-03-09 16:03:07.935833

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b269babcdcd7'
down_revision: Union[str, Sequence[str], None] = '1e1a58ec374d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('files',
                    sa.Column('id', sa.Integer, primary_key=True,
                              autoincrement=True),
                    sa.Column('file_name', sa.String(100),
                              nullable=False),
                    sa.Column('storage_key', sa.String,
                              nullable=False, unique=True),
                    sa.Column('file_size', sa.String, nullable=False),
                    sa.Column('file_type', sa.String, nullable=False),
                    sa.Column('created_by', sa.Integer, sa.ForeignKey(
                        "users.id"), nullable=False),
                    sa.Column('created_at', sa.DateTime,
                              server_default=sa.func.now())
                    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('files')
