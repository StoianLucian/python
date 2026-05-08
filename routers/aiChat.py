from fastapi import APIRouter, Body, Depends, HTTPException
from schemas import *
from fastapi.responses import StreamingResponse
import logging
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


@router.post("/")
def chat(body: ChatRequest = Body(...)):
    prompt = body.prompt
    model = body.model
    logging.info(f"aiChat.chat prompt: {prompt}")

    def generate():
        stream = client.generate(
            model=model,
            prompt=prompt,
            stream=True
        )
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
