CREATE_USER = """
    INSERT INTO users (username, email, password)
    VALUES (%s, %s, %s)
    RETURNING id
"""

GET_ALL_USERS = """
    SELECT id, username, email 
    FROM users
"""

GET_USER_BY_ID = """
    SELECT id, username, email
    FROM users
    WHERE id = %s
"""

DELETE_USER_BY_ID = """
    DELETE FROM users
    WHERE id = %s
"""

CHECK_EXISTING_USER = """
SELECT
    EXISTS(SELECT 1 FROM users WHERE username = %s) AS username_exists,
    EXISTS(SELECT 1 FROM users WHERE email = %s) AS email_exists;
"""
