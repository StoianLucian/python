"""add exercise.type + exercise_entry fields, seed exercise skill & categories

Revision ID: b1e2c3d4f5a6
Revises: a7c3e91f4b28
Create Date: 2026-09-08 12:00:00.000000

"""
from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert


# revision identifiers, used by Alembic.
revision: str = 'b1e2c3d4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a7c3e91f4b28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Lightweight table handles for the seed inserts below.
skills = sa.table(
    "skills",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("key", sa.String),
    sa.column("created_at", sa.Date),
)

exercise_categories = sa.table(
    "exercise_categories",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
)

DEFAULT_EXERCISE_CATEGORIES = [
    "chest", "back", "shoulders", "biceps", "triceps", "forearms", "core",
    "glutes", "quadriceps", "hamstrings", "calves", "hips", "full_body",
    "cardio", "other",
]

def upgrade() -> None:
    """Upgrade schema."""
    # exercises.type — how the exercise is measured ("reps" | "duration").
    # server_default keeps any existing rows valid; the app always sets it.
    op.add_column(
        "exercises",
        sa.Column("type", sa.String(), nullable=False, server_default="reps"),
    )
    op.alter_column("exercises", "type", server_default=None)

    # exercise_entry: reps is now optional (duration exercises have none),
    # plus minutes, computed calories burned, and a denormalized category.
    op.alter_column("exercise_entry", "repetition", nullable=True)
    op.add_column("exercise_entry", sa.Column("minutes", sa.Float(), nullable=True))
    op.add_column(
        "exercise_entry",
        sa.Column("calories", sa.Float(), nullable=False, server_default="0"),
    )
    op.alter_column("exercise_entry", "calories", server_default=None)
    op.add_column(
        "exercise_entry",
        sa.Column("exercise_category", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_exercise_entry_exercise_category",
        "exercise_entry", "exercise_categories",
        ["exercise_category"], ["id"],
    )

    # GIN trigram index for fuzzy exercise-name lookups (pg_trgm already enabled
    # by an earlier migration). Matches the lower(name) used in the repository.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_exercises_name_trgm "
        "ON exercises USING gin (lower(name) gin_trgm_ops)"
    )

    # Seed default muscle-group categories (idempotent).
    op.execute(
        pg_insert(exercise_categories)
        .values([{"name": n} for n in DEFAULT_EXERCISE_CATEGORIES])
        .on_conflict_do_nothing()
    )
    op.execute(
        "SELECT setval("
        "pg_get_serial_sequence('exercise_categories', 'id'), "
        "(SELECT MAX(id) FROM exercise_categories)"
        ")"
    )

    # Seed the /add_exercise skill row (idempotent).
    op.execute(
        "SELECT setval("
        "pg_get_serial_sequence('skills', 'id'), "
        "(SELECT MAX(id) FROM skills)"
        ")"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_exercises_name_trgm")
    op.drop_constraint(
        "fk_exercise_entry_exercise_category", "exercise_entry", type_="foreignkey"
    )
    op.drop_column("exercise_entry", "exercise_category")
    op.drop_column("exercise_entry", "calories")
    op.drop_column("exercise_entry", "minutes")
    op.alter_column("exercise_entry", "repetition", nullable=False)
    op.drop_column("exercises", "type")
