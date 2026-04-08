import shutil
from typing import Any, Dict
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from errors.user import PDFFileSupportedError
from repositories.files_repository import upload_file_db
from schemas import *

from repositories import *
from sql.file_queries import GET_ALL_FILES, GET_FILE_BY_ID

import pdfplumber

router = APIRouter(
    prefix="/files",
    tags=["files"],
)

UPLOAD_FOLDER = "PDFS"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


@router.post("/")
async def create_file(file: UploadFile = File(...), user=Depends(check_token)):
    if file.content_type != "application/pdf":
        raise PDFFileSupportedError()

    filename = file.filename
    storage_key = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, storage_key)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

            upload_file_db(filename, storage_key, file.size,
                           file.content_type, user["user_id"])

            # // extract page contents
        extract_text_from_pdf(file_path)

    except Exception as e:
        # Optional: remove partial file if error occurs
        if os.path.exists(file_path):
            os.remove(file_path)
        raise e  # re-raise so FastAPI returns 500

    # body can be anything: dict, list, string, number, etc.


@router.get("/")
async def get_files(user=Depends(check_token)):
    with db_cursor(cursor_type="dict") as (_, cursor):
        cursor.execute(GET_ALL_FILES, (user["user_id"],))
        files = cursor.fetchall()
        return files


@router.get("/{id}")
async def get_file(id, user=Depends(check_token)):
    with db_cursor() as (_, cursor):
        cursor.execute(GET_FILE_BY_ID, (id,))
        file = cursor.fetchone()

        file_path = os.path.join(UPLOAD_FOLDER, file.storage_key)
        return FileResponse(
            path=file_path,
            filename=file.file_name,  # original file name for download
            media_type="application/pdf"  # adjust based on file type
        )


@router.delete("/{id}")
async def delete_file(id, user=Depends(check_token)):
    with db_cursor() as (_, cursor):
        cursor.execute(DELETE_FILE_BY_ID, (id,))
