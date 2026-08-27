"""enable pg_trgm and add trigram index on food_products.name

Revision ID: c4f1a2b7d3e0
Revises: b269babcdcd7
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c4f1a2b7d3e0'
down_revision: Union[str, Sequence[str], None] = 'b269babcdcd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable trigram matching for fuzzy product-name lookups."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # GIN trigram index on lower(name) so similarity()/% stay fast as the
    # catalog grows. Matches the lower(name) expression used in the repository.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_food_products_name_trgm "
        "ON food_products USING gin (lower(name) gin_trgm_ops)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_food_products_name_trgm")
    # Leave the extension in place: other objects may depend on it.
