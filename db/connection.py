from config.db_config import DB_CONFIG
import psycopg2
from psycopg2 import Error
print("Pachet mysql-connector este vizibil!")

def get_connection(main=True):
    db_name = DB_CONFIG["main_database"] if main else DB_CONFIG["embeddings_database"]
        
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            dbname=db_name,
            port=DB_CONFIG.get("port", 5432)
        )
        print(f"Conexiune la PostgreSQL {db_name} realizată cu succes!")
        return conn
    except Error as e:
        print(f"Eroare la conectarea PostgreSQL: {e}")
        return None

def close_connection(conn):
    if conn:
        conn.close()
        print(f"Conexiunea PostgreSQL a fost închisă.")
