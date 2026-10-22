import base64
import logging
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, load_only
import pdfplumber
from db.schemas.file import (
    File as FileModel,
    FILE_STATUS_DONE,
    FILE_STATUS_FAILED,
    FILE_STATUS_PROCESSING,
)
from errors.user import EmptyPDFFileError, NoVisionModelError, PDFFileSupportedError
from helpers.helpers import sanitize_input, split_sentences
from lmm.factory import get_lmm_provider
from repositories.ai_chat_repository import get_embedding, return_available_embedding_models
from repositories.files_repository import upload_file_db, reset_files_db, delete_file_db, UPLOAD_FOLDER
from repositories.auth_repository import check_token
from db.connection import SessionLocal, get_db
from semantic_text_splitter import TextSplitter
from tqdm import tqdm
from db.schemas.chunk import Chunk

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/files",
    tags=["files"],
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

PDF_CONTENT_TYPE = "application/pdf"
# Image formats we accept and can caption. Mirrors the magic-byte sniffing in
# GoogleProvider._guess_image_mime so what we store matches what the vision
# model can interpret.
IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
ALLOWED_CONTENT_TYPES = {PDF_CONTENT_TYPE, *IMAGE_CONTENT_TYPES}

# Asks a vision model for a search-friendly description. Images have no text of
# their own to embed, so this caption is what lands in the vector pool and makes
# the image retrievable alongside PDF chunks.
IMAGE_CAPTION_PROMPT = (
    "Describe this image in detail so it can be found later by a text search. "
    "Transcribe any visible text verbatim, and note the objects, people, "
    "charts, diagrams, colours and overall context. "
    "Reply with only the description, no preamble."
)


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


def _split_text_pieces(text: str, page_number: int):
    """Split `text` into the windows we embed, WITHOUT embedding them. Returns
    `[{"page_number", "content"}, ...]`. Splitting is cheap and lets us know the
    total chunk count up front so the background job can report progress."""
    splitter = TextSplitter(400)
    chunk_sentences = build_chunks(splitter.chunks(sanitize_input(text)))

    return [
        {"page_number": page_number, "content": " ".join(chunk_sentence)}
        for chunk_sentence in chunk_sentences
    ]


def split_pdf_pieces(file_path: str):
    """Extract each PDF page's text and split it into (unembedded) pieces."""
    pieces = []

    with pdfplumber.open(file_path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            page_text = page.extract_text()

            if not page_text:
                continue

            pieces.extend(_split_text_pieces(page_text, page_index + 1))

    return pieces


def build_image_pieces(image_bytes: bytes, provider):
    """Caption an image and split the caption into (unembedded) pieces so the
    image is searchable in the same chunk pool as document text."""
    caption = caption_image(image_bytes, provider)

    if not caption:
        return []

    return _split_text_pieces(caption, page_number=1)


def _select_vision_model(provider) -> str:
    """Pick a vision-capable chat model from the active provider. Prefers a
    "flash"-class model when present (cheaper/faster on Gemini; a harmless no-op
    for providers without one)."""
    vision_models = [m for m in provider.list_models() if m.get("vision")]

    if not vision_models:
        raise NoVisionModelError()

    for model in vision_models:
        if "flash" in model["id"].lower():
            return model["name"]

    return vision_models[0]["name"]


def _response_text(response) -> str:
    """Pull the assistant's text out of a non-streaming chat response, across
    providers: Gemini exposes `.text`, Ollama puts it on `message.content`."""
    text = getattr(response, "text", None)
    if text:
        return text

    message = getattr(response, "message", None)
    if message is not None:
        return getattr(message, "content", None) or ""

    if isinstance(response, dict):
        return (response.get("message") or {}).get("content") or ""

    return ""


def caption_image(image_bytes: bytes, provider) -> str:
    """Ask a vision model to describe an image. The bytes are sent as base64
    (no data-URL prefix) in the message's `images` list, which both the Ollama
    and Gemini providers understand."""
    model = _select_vision_model(provider)

    b64 = base64.b64encode(image_bytes).decode("ascii")
    messages = [
        {"role": "user", "content": IMAGE_CAPTION_PROMPT, "images": [b64]},
    ]

    response = provider.chat(model=model, messages=messages, stream=False)

    return _response_text(response).strip()


def process_file_embedding(file_id: int, file_path: str, is_image: bool, user_id: int):
    """Background task: parse/split the stored file, embed each chunk, and record
    progress on the `files` row so the UI can poll it. Runs after the upload
    response is sent, with its own DB session (the request's session is closed by
    then)."""
    db = SessionLocal()
    try:
        file = db.query(FileModel).filter(FileModel.id == file_id).first()
        if file is None:
            return

        file.status = FILE_STATUS_PROCESSING
        db.commit()

        embed_model = return_available_embedding_models()[0]["name"]

        if is_image:
            with open(file_path, "rb") as handle:
                image_bytes = handle.read()
            pieces = build_image_pieces(image_bytes, get_lmm_provider())
        else:
            pieces = split_pdf_pieces(file_path)

        file.chunks_total = len(pieces)
        file.chunks_done = 0
        db.commit()

        # tqdm tracks the embedding loop so we get a smoothed rate + ETA for
        # free; it logs to stderr and we read `format_dict` to persist the ETA.
        progress = tqdm(total=len(pieces), desc=f"embed file {file_id}", unit="chunk")
        for index, piece in enumerate(pieces):
            embedding = get_embedding(text=piece["content"], model=embed_model)
            db.add(Chunk(
                document_id=file_id,
                page_number=piece["page_number"],
                content=piece["content"],
                embedding=embedding,
                created_at=datetime.utcnow(),
                created_by=user_id,
            ))
            file.chunks_done = index + 1

            progress.update(1)
            stats = progress.format_dict
            rate = stats.get("rate")
            remaining = stats["total"] - stats["n"]
            file.eta_seconds = int(remaining / rate) if rate else None

            # Commit per chunk so the polled progress advances live.
            db.commit()
        progress.close()

        file.status = FILE_STATUS_DONE
        file.eta_seconds = 0
        db.commit()

    except Exception as e:
        logger.exception("process_file_embedding failed for file %s", file_id)
        db.rollback()
        # Surface the failure on the row rather than leaving it stuck "processing".
        file = db.query(FileModel).filter(FileModel.id == file_id).first()
        if file is not None:
            file.status = FILE_STATUS_FAILED
            file.error = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/", status_code=202)
async def create_file(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    user=Depends(check_token),
    db: Session = Depends(get_db)
):
    """Accept one or more files. Each is validated and saved immediately, then
    its embedding is scheduled as a background task; the response returns right
    away with the created rows (status "pending"). Poll `GET /files` or
    `GET /files/{id}/progress` to watch embedding progress."""
    # Validate everything before persisting anything, so a bad file in the batch
    # doesn't leave half the uploads committed.
    staged = []
    for file in files:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise PDFFileSupportedError()
        content = await file.read()
        if not content:
            raise EmptyPDFFileError()
        staged.append((file.filename, file.content_type, content))

    created = []
    try:
        for filename, content_type, content in staged:
            storage_key = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, storage_key)

            with open(file_path, "wb") as buffer:
                buffer.write(content)

            stored_file = upload_file_db(
                filename,
                storage_key,
                len(content),
                content_type,
                user["user_id"],
                db
            )

            is_image = content_type in IMAGE_CONTENT_TYPES
            background_tasks.add_task(
                process_file_embedding,
                stored_file.id,
                file_path,
                is_image,
                user["user_id"],
            )

            created.append({
                "id": stored_file.id,
                "filename": filename,
                "size": len(content),
                "status": stored_file.status,
            })

        return {"files": created}

    except Exception as e:
        db.rollback()
        raise e


@router.get("/")
async def get_files(user=Depends(check_token), db: Session = Depends(get_db)):

    files = db.query(FileModel).options(load_only(
        FileModel.file_name, FileModel.id, FileModel.created_at,
        FileModel.file_size, FileModel.file_type, FileModel.status,
        FileModel.chunks_done, FileModel.chunks_total, FileModel.eta_seconds,
        FileModel.error,
    )).filter(
        FileModel.created_by == user["user_id"]).all()

    return files


@router.get("/{id}/chunks")
async def get_file_chunks(id: int, user=Depends(check_token), db: Session = Depends(get_db)):
    """List the document chunks for one file (content + page), without the
    embedding vector. Shown when the file is expanded in the UI."""
    file = db.query(FileModel.id).filter(
        FileModel.id == id,
        FileModel.created_by == user["user_id"],
    ).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    rows = (
        db.query(Chunk.id, Chunk.page_number, Chunk.content)
        .filter(
            Chunk.document_id == id,
            Chunk.created_by == user["user_id"],
            Chunk.source_type == "document",
        )
        .order_by(Chunk.page_number, Chunk.id)
        .all()
    )

    return [
        {"id": row.id, "page_number": row.page_number, "content": row.content}
        for row in rows
    ]


@router.get("/{id}/progress")
async def get_file_progress(id: int, user=Depends(check_token), db: Session = Depends(get_db)):
    """Embedding progress for one file, for polling after upload."""
    file = db.query(FileModel).options(load_only(
        FileModel.id, FileModel.status, FileModel.chunks_done,
        FileModel.chunks_total, FileModel.eta_seconds, FileModel.error,
    )).filter(
        FileModel.id == id,
        FileModel.created_by == user["user_id"],
    ).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "id": file.id,
        "status": file.status,
        "chunks_done": file.chunks_done,
        "chunks_total": file.chunks_total,
        "eta_seconds": file.eta_seconds,
        "error": file.error,
    }


@router.get("/{id}")
async def get_file(id: int, user=Depends(check_token), db: Session = Depends(get_db)):
    file = db.query(FileModel).filter(FileModel.id == id,
                                      FileModel.created_by == user["user_id"]).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = os.path.join(UPLOAD_FOLDER, file.storage_key)

    if not os.path.exists(file_path):
        # The backing file is gone, so the DB entry is orphaned — prune it (and
        # its chunks) before reporting the file as missing.
        delete_file_db(db, file)
        raise HTTPException(status_code=404, detail="File missing on disk")

    return FileResponse(
        path=file_path,
        filename=file.file_name,
        # Serve the type we stored on upload so images come back as images, not
        # as application/pdf.
        media_type=file.file_type or "application/octet-stream"
    )


@router.get("/{id}/exists")
async def file_exists(id: int, user=Depends(check_token), db: Session = Depends(get_db)):
    # Lightweight presence probe for the UI (green check / red X). Unlike the
    # download route it never streams the file and never prunes orphaned rows —
    # it's a pure read so merely rendering a citation can't mutate anything.
    file = db.query(FileModel).filter(FileModel.id == id,
                                      FileModel.created_by == user["user_id"]).first()
    if not file:
        return {"exists": False}

    file_path = os.path.join(UPLOAD_FOLDER, file.storage_key)
    return {"exists": os.path.exists(file_path)}


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
def reset_files(db: Session = Depends(get_db), user=Depends(check_token)):

    try:
        result = reset_files_db(db, user["user_id"])

        if result:
            return {"status": "ok"}
    except Exception as e:
        raise e
