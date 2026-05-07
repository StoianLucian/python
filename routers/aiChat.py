from fastapi import APIRouter, Body, Depends, HTTPException
from schemas import *
from fastapi.responses import StreamingResponse
import logging
from ollama import Client


from repositories import *

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


class ChatRequest(BaseModel):
    prompt: str


client = Client(
    host="https://ducky-pork-bleach.ngrok-free.dev"
)


@router.post("/")
def chat(body: ChatRequest = Body(...)):
    prompt = body.prompt
    logging.info(f"aiChat.chat prompt: {prompt}")

    def generate():
        stream = client.generate(
            model="deepseek-r1:1.5b",
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
