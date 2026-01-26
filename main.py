from db.connection import get_connection, close_connection


conn = get_connection()

if conn:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        version = cursor.fetchone()
        print(f"Conectat la baza de date: {version[0]} 1")
    except Exception as e:
        print(f"Eroare la interogarea bazei de date: {e}")
    finally:
        cursor.close()