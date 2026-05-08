import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, load_only

import pdfplumber

from db.schemas.file import File as FileModel

from errors.user import EmptyPDFFileError, PDFFileSupportedError
from repositories.files_repository import upload_file_db
from repositories.auth_repository import check_token
from db.connection import get_db

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
async def create_file(
    file: UploadFile = File(...),
    user=Depends(check_token),
    db: Session = Depends(get_db)
):
    if file.content_type != "application/pdf":
        raise PDFFileSupportedError()

    filename = file.filename
    storage_key = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, storage_key)

    try:
        content = await file.read()

        if not content:
            raise EmptyPDFFileError()

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # ✅ STORE IN DB
        upload_file_db(
            filename,
            storage_key,
            len(content),  # safer than file.size
            file.content_type,
            user["user_id"],
            db
        )

        # ✅ EXTRACT TEXT
        text = extract_text_from_pdf(file_path)

        return {
            "filename": filename,
            "size": len(content),
            "preview": text[:200]
        }

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise e


@router.get("/")
async def get_files(user=Depends(check_token), db: Session = Depends(get_db)):

    print("here")
    files = db.query(FileModel).options(load_only(FileModel.file_name, FileModel.id)).filter(
        FileModel.created_by == user["user_id"]).all()

    return files


@router.get("/{id}")
async def get_file(id: int, user=Depends(check_token), db: Session = Depends(get_db)):
    file = db.query(FileModel).filter(FileModel.id == id,
                                      FileModel.created_by == user["user_id"]).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = os.path.join(UPLOAD_FOLDER, file.storage_key)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File missing on disk")

    return FileResponse(
        path=file_path,
        filename=file.file_name,
        media_type="application/pdf"
    )


@router.delete("/{id}")
async def delete_file(id: int, user=Depends(check_token), db: Session = Depends(get_db)):
    file = db.query(FileModel).filter(FileModel.id == id,
                                      FileModel.created_by == user["user_id"]).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    db.delete(file)
    db.commit()
    return {"status": "ok"}
