from typing import Optional

from fastapi import APIRouter, Depends
from db.connection import get_db
from db.schemas.chunk import Chunk
from helpers.helpers import return_context
from repositories.aiChat_repository import initialize_model_chat, is_model_installed, return_available_models
from prompts.prompts import rag_prompt
from schemas import *
from fastapi.responses import StreamingResponse
import json
from ollama import Client
import os
from sqlalchemy import select


from repositories import *

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


class ChatRequest(BaseModel):
    prompt: str
    model: str


modelUrl = os.getenv("MODEL_URL")

client = Client(
    host=modelUrl
)


class Message(BaseModel):
    role: str
    content: str
    images: Optional[list[str]] = None


class ChatRequestTest(BaseModel):
    messages: list[Message]
    model: str


@router.post("/")
def chat(body: ChatRequestTest,  db: Session = Depends(get_db)):
    messages = body.messages
    model = body.model

    last_message = messages[-1].content

    context = return_context(last_message, db)

    test_prompt = rag_prompt.format(
        context=context, user_question=last_message)

    messages = [
        {
            "role": "system",
            "content": test_prompt
        },
        *[
            {
                "role": m.role,
                "content": m.content
            }
            for m in body.messages
        ]
    ]

    def generate():
        stream = initialize_model_chat(model, messages, True)

        for chunk in stream:

            content = chunk.get("message", {}).get("content")
            thinking = chunk.get("message", {}).get("thinking")
            isDone = chunk.get("done")

            if content or thinking:
                yield json.dumps({
                    "content": content,
                    "thinking": thinking,
                    "done": isDone
                }) + "\n"

            if chunk.get("done"):
                break

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )


class ChatRequest(BaseModel):
    model: str


@router.post("/ping")
def chat(body: ChatRequest):
    model = body.model
  
    try:
        return is_model_installed(model)
    except Exception as e:
        raise e


@router.get("/models")
def return_models():
    try:
        models = return_available_models()
        return models
    except Exception as e:
        raise e
