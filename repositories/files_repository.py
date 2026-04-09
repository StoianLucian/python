import string
from sqlalchemy.orm import Session
from db.schemas.file import File


def upload_file_db(filename: string, storageKey: string, size: int, type: string, createdBy: string, db: Session):

    file = File(
        file_name=filename,
        storage_key=storageKey,
        file_size=size,
        file_type=type,
        created_by=createdBy,
    )

    db.add(file)
    db.commit()
    db.refresh(file)

    return file
