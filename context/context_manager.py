from contextlib import contextmanager
import psycopg2.extras
from db.connection import get_connection

@contextmanager
def db_cursor(main_db = True,cursor_type="namedtuple"):
    conn = get_connection(main_db)
    if not conn:
        raise Exception("Nu s-a putut crea conexiunea la DB")

    if cursor_type == "dict":
        cursor_factory = psycopg2.extras.RealDictCursor
    elif cursor_type == "namedtuple": # classic user.id example
        cursor_factory = psycopg2.extras.NamedTupleCursor
    else:
        cursor_factory = None 

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
