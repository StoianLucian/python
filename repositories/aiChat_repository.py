from ollama import Client
import os

modelUrl = os.getenv("MODEL_URL")

client = Client(
    host=modelUrl
)


def initialize_model(model: str, prompt: str, stream: bool):
    response = client.generate(
        model=model,
        prompt=prompt,
        stream=stream
    )

    return response
