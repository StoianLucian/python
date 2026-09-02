import os

DB_CONFIG = {
    "host": "localhost",
    "user": "postgres",
    "password": "",
    "main_database": "python_postgress",
    "port": 5432,
    "embeddings_database" : "python_embeddings_db"
}
# https://ducky-pork-bleach.ngrok-free.dev


def resolve_db_url() -> str:
    """Resolve the database URL for the app and migrations.

    Prefers the ``DB_URL`` env var, then ``DATABASE_URL`` (the name Render's
    managed Postgres injects automatically), and finally falls back to a
    localhost URL built from ``DB_CONFIG`` for local development.

    SQLAlchemy 2.x rejects the legacy ``postgres://`` scheme that some hosts
    (Render, Heroku) hand out, so we normalize it to ``postgresql://``.
    """
    url = os.getenv("DB_URL") or os.getenv("DATABASE_URL")
    if not url:
        url = (
            f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
            f"@{DB_CONFIG['host']}:{DB_CONFIG.get('port', 5432)}"
            f"/{DB_CONFIG['main_database']}"
        )
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url