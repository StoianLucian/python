import string
from sqlalchemy.orm import Session
from db.schemas.file import File
from db.schemas.chunk import Chunk
from datetime import datetime
import logging


def upload_file_db(filename: string, storageKey: string, size: int, type: string, createdBy: string, db: Session):

    logging.debug("files_repository.upload_file_db", [
                  filename, storageKey, size, type, createdBy])

    file = File(
        file_name=filename,
        storage_key=storageKey,
        file_size=size,
        file_type=type,
        created_by=createdBy,
        created_at=datetime.now()
    )

    db.add(file)
    db.commit()
    db.refresh(file)

    return file

def reset_files_db(db: Session, user_id: int):
    try:
        db.query(File).filter(File.created_by == user_id).delete(synchronize_session=False)
        db.query(Chunk).filter(Chunk.created_by == user_id).delete(synchronize_session=False)
        db.commit()
        
        return True
    except Exception:
        db.rollback()
        raise
    