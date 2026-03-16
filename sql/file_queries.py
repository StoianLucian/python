CREATE_FILE = """
    INSERT INTO files (file_name, storage_key, file_size, file_type, created_by)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id
"""

GET_ALL_FILES = """
    SELECT id, file_name, storage_key
    FROM files
    WHERE created_by = %s
"""
