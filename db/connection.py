from config.db_config import DB_CONFIG
import psycopg2
from psycopg2 import Error
print("Pachet mysql-connector este vizibil!")

def get_connection():
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            dbname=DB_CONFIG["database"],
            port=DB_CONFIG.get("port", 5432)
        )
        print("Conexiune la PostgreSQL realizată cu succes!")
        return conn
    except Error as e:
        print(f"Eroare la conectarea PostgreSQL: {e}")
        return None

def close_connection(conn):
    if conn:
        conn.close()
        print("Conexiunea PostgreSQL a fost închisă.")
