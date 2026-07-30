from datetime import datetime
from typing import Any, Optional

from db.connection import get_db
from ollama import Client, ResponseError
import os

from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.schemas.user import User
from difflib import get_close_matches

from db.schemas.chunk import Chunk

modelUrl = os.getenv("MODEL_URL")

client = Client(
    host=modelUrl
)

session_summary_options = {
    "temperature": 0,
    "top_p": 0.8,
    "keep_alive": "1m"
}


def is_model_installed(model_name: str) -> bool:
    try:
        client.show(model_name)
        return True
    except ResponseError as e:
        print(e)
        return False
    

def initialize_model_generate(model: str, prompt: str, stream: bool = False, options: Optional[dict] = None):
    response = client.generate(
        model=model,
        prompt=prompt,
        stream=stream,
        options=options
    )

    return response


class Message(BaseModel):
    role: str
    content: str
    images: Optional[list[str]] = None


def get_embedding(text: str, model):
    response = client.embeddings(
        model=model,
        prompt=text
    )
    return response["embedding"]



def initialize_model_chat(model: str, messages: list[Message], stream: bool, options: Optional[dict] = None, tools: Optional[dict] = None, format= None, thinking = False):
    
    parsed_messages = [
            m.model_dump() if hasattr(m, "model_dump") else m
            for m in messages
        ]
    kwargs = {
        "model":model,
        "messages": parsed_messages,
        "stream": stream,
        "options": options,
    }
    
    if tools is not None:
        kwargs["tools"] = tools
        
    if format is not None:
        kwargs["format"] = format
        
    if thinking is not None:
        kwargs["think"] = thinking
    try:
        chat = client.chat(
           **kwargs
        )
        return chat
    
    except Exception as e:
        raise e


def return_available_models():

    try:
        models = client.list()

        model_names = [
            {
                "name": m["model"],
                "id": m["model"]
            }
            for m in models["models"]
            if "embed" not in m["model"].lower()
        ]

        return model_names
    except Exception as e:
        raise e


def return_available_embedding_models():
    models = client.list()

    model_names = [
        {
            "name": m["model"],
            "id": m["model"]
        }
        for m in models["models"]
        if "embed" in m["model"].lower()
    ]

    return model_names

def return_smallest_model():
    try:
        models = client.list()["models"]

        # Ignore embedding models
        models = [
            m for m in models
            if "embed" not in m["model"].lower()
        ]

        smallest = min(models, key=lambda m: m["size"])

        return smallest["model"]

    except Exception as e:
        raise e


def create_chunk(chunk_obj, file_id: int, user_id: int, db: Session):
    db.add_all(
        Chunk(
            document_id=file_id,
            page_number=chunk["page_number"],
            content=chunk["content"],
            embedding=chunk["embedding"],
            created_at=datetime.utcnow(),
            created_by=user_id,
        )
        for chunk in chunk_obj
    )

    db.commit()
