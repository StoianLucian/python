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


@router.post("/")
def chat(body: ChatRequest):
    prompt = body.prompt
    model = body.model
    logging.info(f"aiChat.chat prompt: {prompt}")

    def generate():
        stream = initialize_model(model, prompt, True)

        for chunk in stream:

            response = chunk.get("response")
            thinking = chunk.get("thinking")

            if response is not None or thinking is not None:
                yield json.dumps({
                    "response": response,
                    "thinking": thinking,
                }) + "\n"

            if chunk.get("done"):
                break

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )


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


@router.post("/test")
def chat(body: ChatRequestTest):

    response = client.chat(
        model=body.model,
        messages=[m.model_dump() for m in body.messages],
        stream=False
    )

    return response


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
