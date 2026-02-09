"""alter_users_table_add_password_column

Revision ID: 1e1a58ec374d
Revises: 625a481f6c4a
Create Date: 2026-01-20 14:00:30.528428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e1a58ec374d'
down_revision: Union[str, Sequence[str], None] = '625a481f6c4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('password', sa.String(255), nullable=False))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'password')