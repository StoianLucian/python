"""create_users_table

Revision ID: 625a481f6c4a
Revises: 
Create Date: 2026-01-19 15:23:37.731890

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '625a481f6c4a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
                    sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
                    sa.Column('username', sa.String(100), nullable=False, unique=True),
                    sa.Column('email', sa.String(100), nullable=False, unique=True),
                    sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )

def downgrade() -> None:
    op.drop_table('users')
