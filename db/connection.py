import mysql.connector
from mysql.connector import Error
from config.db_config import DB_CONFIG
print("Pachet mysql-connector este vizibil!")

def get_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"]
        )
        if conn.is_connected():
            print("Conexiune la baza de date MySQL realizata cu succes!")
            return conn
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None

def close_connection(conn):
    if conn and conn.is_connected():
        conn.close()
        print("Conexiunea la baza de date MySQL a fost inchisa.")