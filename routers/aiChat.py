from fastapi import APIRouter, Body, Depends, HTTPException
from repositories.aiChat_repository import initialize_model
from schemas import *
from fastapi.responses import StreamingResponse
import logging


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
            if response:
                yield response

            if chunk.get("done"):
                break

    return StreamingResponse(
        generate(),
        media_type="text/plain"
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
