import string

from context.context_manager import db_cursor
from sql.file_queries import CREATE_FILE


def upload_file_db(filename: string, storageKey: string, size: int, type: string, createdBy: string):
    print({filename, storageKey, size, type, createdBy})
    with db_cursor() as (_, cursor):  # <-- ai nevoie de ()

        cursor.execute(
            CREATE_FILE,
            (filename, storageKey, size, type, createdBy)
        )

        return {
            "uploaded_by": createdBy,
            "filename": filename,
            "content_type": type,
            "size": size
        }
        
