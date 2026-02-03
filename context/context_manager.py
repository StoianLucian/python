from contextlib import contextmanager
import psycopg2.extras
from db.connection import get_connection

@contextmanager
def db_cursor(dictionary=True):
    conn = get_connection()
    if not conn:
        raise Exception("Nu s-a putut crea conexiunea la DB")

    cursor_factory = (
        psycopg2.extras.RealDictCursor if dictionary else None
    )

    cursor = conn.cursor(cursor_factory=cursor_factory)

    try:
        yield conn, cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
