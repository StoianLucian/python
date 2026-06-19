from typing import Optional

from fastapi import APIRouter
from repositories.aiChat_repository import get_embedding, initialize_model_chat, initialize_model_generate, ping_options, return_available_embedding_models, return_available_models
from schemas import *
from fastapi.responses import StreamingResponse
import logging
import json
from ollama import Client
import os


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
def chat(body: ChatRequestTest):
    messages = body.messages
    model = body.model

    last_message = messages[-1].content
    embedding_models = return_available_embedding_models()
    embedding = get_embedding(
        text=last_message,
        model=embedding_models[0]["name"]
    )
    
    messages[-1].content = "modified value"

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
        response = initialize_model_generate(
            model, "Ping", False, ping_options)

        return_models()
        if not response.get("response"):
            return False

        return True
    except Exception as e:
        raise e


@router.get("/models")
def return_models():
    try:
        models = return_available_models()
        return models
    except Exception as e:
        raise e
