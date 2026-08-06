from ollama import Client
from .provider import LMMProvider

class OllamaProvider(LMMProvider):
    def __init__(self, host: str):
        self.client = Client(host)

    def chat(
        self,
        model,
        messages,
        stream=False,
        tools=None,
        options=None,
        thinking=False,
    ):
        kwargs = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": options,
            "think": thinking,
        }

        if tools:
            kwargs["tools"] = tools

        return self.client.chat(**kwargs)