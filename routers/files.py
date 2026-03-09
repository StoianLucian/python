import shutil
from typing import Any, Dict
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from errors.user import PDFFileSupportedError
from schemas import *
from helpers.helpers import raise_error

from errors import UserErrorCode
from repositories import *

router = APIRouter(
    prefix="/files",
    tags=["files"],
)

UPLOAD_FOLDER = "PDFS"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.post("/")
async def create_file(file: UploadFile = File(...), user=Depends(check_token)):
    if file.content_type != "application/pdf":
        raise PDFFileSupportedError()

    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        
    except Exception as e:
        # Optional: remove partial file if error occurs
        if os.path.exists(file_path):
            os.remove(file_path)
        raise e  # re-raise so FastAPI returns 500

    size = os.path.getsize(file_path)

    # body can be anything: dict, list, string, number, etc.
    return {
        "uploaded_by": user["user_id"],
        "filename": filename,
        "content_type": file.content_type,
        "size": size
    }
