LOGIN_USER = """
SELECT id, username, email, password
FROM users
WHERE username = %s
   OR email = %s
"""