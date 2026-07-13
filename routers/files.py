import os
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, load_only
import pdfplumber
from db.schemas.file import File as FileModel
from errors.user import EmptyPDFFileError, PDFFileSupportedError
from helpers.helpers import sanitize_input, split_sentences
from repositories.aiChat_repository import get_embedding, return_available_embedding_models
from repositories.files_repository import upload_file_db, reset_files_db
from repositories.auth_repository import check_token
from db.connection import get_db
from repositories.aiChat_repository import create_chunk
from semantic_text_splitter import TextSplitter
from db.schemas.chunk import Chunk

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


def build_chunks(sentences, chunk_size=3, overlap=1):
    chunks = []

    step = chunk_size - overlap

    for i in range(0, len(sentences), step):
        chunk = sentences[i:i + chunk_size]

        if chunk:
            chunks.append(chunk)

        if len(chunk) < chunk_size:
            break

    return chunks


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

        file = upload_file_db(
            filename,
            storage_key,
            len(content),
            file.content_type,
            user["user_id"],
            db
        )

        embedding_models = return_available_embedding_models()

        chunks = []

        with pdfplumber.open(file_path) as pdf:
            for page_index, page in enumerate(pdf.pages):
                page_text = page.extract_text()

                if not page_text:
                    continue
                
                splitter = TextSplitter(400)
                
                split_text = splitter.chunks(sanitize_input(page_text))
                
                chunk_sentences = build_chunks(split_text)

                for chunk_index, chunk_sentence in enumerate(chunk_sentences):
                    content = " ".join(chunk_sentence)


                    embedding = get_embedding(
                        text=content,
                        model=embedding_models[0]["name"]
                    )

                    
                    chunk = {
                        "page_number": page_index + 1,
                        "page_title": "some title",
                        "chunk_index": chunk_index,
                        "content": content,
                        "embedding": embedding,
                    }

                    chunks.append(chunk)
                    
        print(chunks[-1], "----")
                    
        # print(chunks)
        create_chunk(chunks, file.id, user["user_id"], db)

        return {
            "filename": filename,
            "size": len(content)
        }

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        db.rollback()
        raise e

@router.get("/")
async def get_files(user=Depends(check_token), db: Session = Depends(get_db)):

    files = db.query(FileModel).options(load_only(FileModel.file_name, FileModel.id, FileModel.created_at, FileModel.file_size, FileModel.file_type)).filter(
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
    
    chunk = db.query(chunk)
    db.delete(file)
    db.commit()
    return {"status": "ok"}

@router.delete('/')
def reset_files(db: Session = Depends(get_db), user = Depends(check_token)):
    
    try:
        result = reset_files_db(db, user["user_id"])
        
        if result:
            return {"status": "ok"}
    except Exception as e:
        raise e
    
