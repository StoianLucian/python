import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, load_only

import pdfplumber

from db.schemas.file import File as FileModel

from repositories.files_repository import upload_file_db
from repositories import check_token, get_db

router = APIRouter(
    prefix="/test",
    tags=["test"],
)


@router.get("/")
async def test():
   

    return "ping"
