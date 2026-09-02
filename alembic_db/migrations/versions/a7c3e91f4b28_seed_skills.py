"""seed skills table

Revision ID: a7c3e91f4b28
Revises: c4f1a2b7d3e0
Create Date: 2026-09-02 11:30:30.000000

"""
from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert


# revision identifiers, used by Alembic.
revision: str = 'a7c3e91f4b28'
down_revision: Union[str, Sequence[str], None] = 'c4f1a2b7d3e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Lightweight table definition matching db.schemas.skill.Skill, used only for
# the bulk insert/delete below.
skills = sa.table(
    "skills",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("key", sa.String),
    sa.column("created_at", sa.Date),
)

SEED = [
    {"id": 1, "name": "Send Email", "key": "/send_email", "created_at": date(2026, 7, 21)},
    {"id": 2, "name": "Send SMS", "key": "/send_sms", "created_at": date(2026, 7, 21)},
    {"id": 3, "name": "Generate Report", "key": "/generate_report", "created_at": date(2026, 7, 21)},
    {"id": 4, "name": "Create Task", "key": "/create_task", "created_at": date(2026, 7, 21)},
    {"id": 6, "name": "Search Documents", "key": "/search_documents", "created_at": date(2026, 7, 21)},
    {"id": 9, "name": "Get all users", "key": "/users_list", "created_at": date(2026, 7, 21)},
    {"id": 10, "name": "Search Web", "key": "/web_search", "created_at": date(2026, 7, 21)},
    {"id": 11, "name": "Add calories", "key": "/add_calories", "created_at": date(2026, 7, 21)},
    {"id": 12, "name": "Total calories", "key": "/total_calories", "created_at": date(2026, 7, 21)},
]


def upgrade() -> None:
    """Seed the skills catalog. Idempotent: skips rows that already exist so it
    is safe on databases that were populated before this migration."""
    op.execute(pg_insert(skills).values(SEED).on_conflict_do_nothing())
    # Rows carry explicit ids with gaps, so realign the identity sequence to the
    # current max id and keep future autoincrement inserts from colliding.
    op.execute(
        "SELECT setval("
        "pg_get_serial_sequence('skills', 'id'), "
        "(SELECT MAX(id) FROM skills)"
        ")"
    )


def downgrade() -> None:
    """Remove the seeded skills."""
    ids = tuple(row["id"] for row in SEED)
    op.execute(
        sa.delete(skills).where(skills.c.id.in_(ids))
    )
