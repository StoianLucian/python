from fastapi import APIRouter, Body, Depends, HTTPException
from repositories.aiChat_repository import initialize_model
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


class ChatRequestTest(BaseModel):
    messages: list[Message]
    model: str


@router.post("/")
def chat(body: ChatRequestTest):
    messages = body.messages
    model = body.model

    def generate():
        stream = client.chat(
            model=model,
            messages=[m.model_dump() for m in messages],
            stream=True
        )

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
    prompt = "Only return true if you are online"
    model = body.model

    try:
        response = initialize_model(model, prompt, False)
        if not response.get("response"):
            return False

        return True
    except Exception as e:
        raise e
