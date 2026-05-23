from typing import Any, Optional

from ollama import Client
import os

from pydantic import BaseModel

modelUrl = os.getenv("MODEL_URL")

client = Client(
    host=modelUrl
)

# options used to ping model faster
ping_options = {
    "temperature": 0,
    "num_predict": 1,
    "keep_alive": "1m"
}

session_summary_options = {
    "temperature": 0,
    "top_p": 0.8,
    "keep_alive": "1m"
}

session_summary_prompt = """
You are an assistant that creates concise conversation titles.

Instructions:
- Generate a very short summary of the user's prompt.
- Maximum 6 words.
- Return only the summary.
- Do not use quotes or punctuation unless necessary.
- Focus on the main intent/topic.

User prompt:
{user_prompt}
"""


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


def initialize_model_chat(model: str, messages: list[Message], stream: bool, options: Optional[dict] = None):

    parsed_messages = [
        m.model_dump() if hasattr(m, "model_dump") else m
        for m in messages
    ]

    chat = client.chat(
        model=model,
        messages=parsed_messages,
        stream=stream,
        options=options
    )

    return chat


def return_available_models():
    models = client.list()

    model_names = [
        {
            "name": m["name"],
            "id": m["model"]
        }
        for m in models["models"]
    ]

    return model_names


def return_smallest_model():
    models = return_available_models()
    return min(models, key=lambda m: int(m['name'].split(':')[1][:-1]))['name']
