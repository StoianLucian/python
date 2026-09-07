from google import genai
from google.genai import types

from .provider import LMMProvider


class GoogleProvider(LMMProvider):
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def _convert_messages(self, messages):
        contents = []

        for message in messages:
            role = message["role"]
            content = message["content"]

            # Gemini uses "user" and "model"
            if role == "assistant":
                role = "model"

            # Gemini doesn't use "system" as a normal Content role.
            # System instructions should ideally be extracted separately.
            if role == "system":
                continue

            contents.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part.from_text(text=content)
                    ],
                )
            )

        return contents

    def chat(
        self,
        model,
        messages,
        stream=False,
        tools=None,
        options=None,
        thinking=False,
        format=None
    ):
        contents = self._convert_messages(messages)

        config = {}

        if options:
            config.update(options)

        if tools:
            config["tools"] = tools

        if format:
            config["response_mime_type"] = format

        kwargs = {
            "model": model,
            "contents": contents,
        }

        if config:
            kwargs["config"] = types.GenerateContentConfig(**config)

        if stream:
            return self.client.models.generate_content_stream(**kwargs)

        return self.client.models.generate_content(**kwargs)

    def list_models(self):
        return [
            {
                "name": m.display_name or m.name,
                "id": m.name.removeprefix("models/"),
            }
            for m in self.client.models.list()
            if "embed" not in m.name.lower()
            and "generateContent" in (m.supported_actions or [])
        ]

    def is_model_installed(self, model_name: str) -> bool:
        wanted = model_name.removeprefix("models/")
        return any(m["id"] == wanted for m in self.list_models())

    def iter_stream(self, stream):
        # Unlike Ollama, Gemini has no per-chunk "done" flag — the stream simply
        # ends, and the final chunk carries usage_metadata. So we relay text as
        # it arrives and synthesize a single terminal event once the loop ends.
        last = None

        for chunk in stream:
            last = chunk

            try:
                text = chunk.text
            except (ValueError, AttributeError):
                # `.text` raises when a chunk has no text part (e.g. a function
                # call or a safety-blocked chunk); nothing to stream for it.
                text = None

            yield {
                "content": text,
                "thinking": None,
                "done": False,
                "usage": None,
            }

        usage = None
        meta = getattr(last, "usage_metadata", None)
        if meta:
            usage = {
                "input": getattr(meta, "prompt_token_count", 0) or 0,
                "output": getattr(meta, "candidates_token_count", 0) or 0,
            }

        yield {"content": None, "thinking": None, "done": True, "usage": usage}