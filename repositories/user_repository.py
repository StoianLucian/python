from db.connection import get_connection
from sql import CREATE_USER, GET_ALL_USERS, GET_USER_BY_ID, DELETE_USER_BY_ID
from fastapi import HTTPException
from services.security import hash_password
from context.context_manager import db_cursor


def create_user_db(userData):
    with db_cursor() as (_, cursor):  # <-- ai nevoie de ()
        password = hash_password(userData.password)

        cursor.execute(
            CREATE_USER,
            (userData.username, userData.email, password)
        )
        cursor.lastrowid
        return cursor.lastrowid

def get_all_users_db():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(GET_ALL_USERS)
        users = cursor.fetchall()
        return users
    except Exception as e:
        print(f"error getting users: {e}")
        return e
    finally:
        cursor.close()
        conn.close()
        
def get_user_by_id_db(id: int):
    with db_cursor() as (_, cursor):
        cursor.execute(GET_USER_BY_ID, (id,))
        user = cursor.fetchone()
        print(user)
        
        if user is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "User not found",
                    "errorCode": "user_not_found"
                })
        
        return user
    # conn = get_connection()
    # cursor = conn.cursor(dictionary=True)
    
    
    # try:
    #     cursor.execute(GET_USER_BY_ID, (id,))
    #     user = cursor.fetchone()

    #     if user is None:
    #         raise HTTPException(status_code=404, detail="User not found")

    #     return user
    # except Exception as e:
    #     print(f"error getting user with id: {id}, {e}")
    #     return e
    # finally:
    #     cursor.close()
    #     conn.close()
        
def delete_user_by_id_db(id: int) -> bool:
    with db_cursor() as (_, cursor):
        cursor.execute(DELETE_USER_BY_ID, (id,))
        return cursor.rowcount > 0