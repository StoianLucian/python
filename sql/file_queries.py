CREATE_FILE = """
    INSERT INTO documents (file_name, storake_key, created_by)
    VALUES (%s, %s, %s)
    RETURNING id
"""