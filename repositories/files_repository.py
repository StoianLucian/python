import os
import string
from sqlalchemy.orm import Session
from db.schemas.file import File
from db.schemas.chunk import Chunk
from datetime import datetime
import logging

UPLOAD_FOLDER = "PDFS"


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
        storage_keys = [
            key for (key,) in db.query(File.storage_key).filter(
                File.created_by == user_id).all()
        ]

        db.query(File).filter(File.created_by == user_id).delete(
            synchronize_session=False)
        db.query(Chunk).filter(Chunk.created_by ==
                               user_id).delete(synchronize_session=False)
        db.commit()

        for storage_key in storage_keys:
            file_path = os.path.join(UPLOAD_FOLDER, storage_key)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                logging.exception(
                    "files_repository.reset_files_db failed to delete %s",
                    file_path)

        return True
    except Exception:
        db.rollback()
        raise
