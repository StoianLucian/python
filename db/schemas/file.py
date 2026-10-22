from datetime import datetime
from typing import Optional

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.schemas.base import Base

# Embedding happens in a background task, so a file's chunks aren't ready the
# moment the upload returns. These are the lifecycle states the UI polls.
FILE_STATUS_PENDING = "pending"
FILE_STATUS_PROCESSING = "processing"
FILE_STATUS_DONE = "done"
FILE_STATUS_FAILED = "failed"


class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(
        String, unique=True, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(Date, nullable=False)
    # Background embedding progress. `chunks_total` is 0 until the file has been
    # parsed/split; `status` ends at "done" or "failed" (with `error` set).
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=FILE_STATUS_PENDING,
        server_default=FILE_STATUS_PENDING)
    chunks_done: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0")
    chunks_total: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0")
    # Estimated seconds remaining for the embedding job (from tqdm's rate);
    # None until a rate is known, and while not processing.
    eta_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
