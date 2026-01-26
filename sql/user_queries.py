CREATE_USER = """
INSERT INTO users (username, email, password)
VALUES (%s, %s, %s)
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
