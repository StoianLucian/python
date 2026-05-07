from fastapi import APIRouter, Body, Depends, HTTPException
from schemas import *
from fastapi.responses import StreamingResponse
import requests
import json
import logging


from repositories import *

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


class ChatRequest(BaseModel):
    prompt: str


@router.post("/")
def chat(body: ChatRequest = Body(...)):
    prompt = body.prompt

    print("test", prompt)
    return prompt
    def generate():
        with requests.post(
            # "http://localhost:11434/api/generate",
            "https://ducky-pork-bleach.ngrok-free.dev/api/generate",
            json={
                "model": "deepseek-r1:1.5b",
                "prompt": prompt,
                "stream": True
            },
            stream=True
        ) as r:

            for line in r.iter_lines(decode_unicode=True):
                if line:
                    data = json.loads(line)

                    if "response" in data:
                        yield data["response"]

                    if data.get("done"):
                        break

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )
