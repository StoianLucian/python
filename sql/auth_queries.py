LOGIN_USER = """
SELECT id, username, email
FROM users
WHERE username = %s
   OR email = %s
"""