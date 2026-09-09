from google import genai
from google.genai import types

from .provider import LMMProvider


class GoogleProvider(LMMProvider):
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def _convert_messages(self, messages):
        """Split a canonical message list into Gemini `contents` and a single
        `system_instruction` string.

        Messages we build during the tool loop are already native
        ``types.Content`` objects (assistant tool calls, tool results); those
        pass straight through. Plain dict messages (user/assistant text, system)
        are translated. Gemini has no per-turn "system" role, so system text is
        concatenated and returned separately for `GenerateContentConfig`.
        """
        contents = []
        system_parts = []

        for message in messages:
            # Native turns built by build_assistant_message / build_tool_result_message.
            if isinstance(message, types.Content):
                contents.append(message)
                continue

            role = message["role"]
            content = message["content"]

            if role == "system":
                if content:
                    system_parts.append(content)
                continue

            # Gemini uses "user" and "model".
            if role == "assistant":
                role = "model"

            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=content)],
                )
            )

        system_instruction = "\n\n".join(system_parts) or None
        return contents, system_instruction

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
        contents, system_instruction = self._convert_messages(messages)

        config = {}

        if options:
            config.update(options)

        if system_instruction:
            config["system_instruction"] = system_instruction

        if thinking:
            # Opt into reasoning and ask for thought summaries so `iter_stream`
            # can route them to the "thinking" channel. Only set when enabled:
            # sending thinking_config to a non-thinking model would error, and
            # thinking-capable models reason by default anyway.
            config["thinking_config"] = types.ThinkingConfig(include_thoughts=True)

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
                # Gemini reports thinking support directly on the model listing.
                "thinking": bool(getattr(m, "thinking", False)),
            }
            for m in self.client.models.list()
            if "embed" not in m.name.lower()
            and "generateContent" in (m.supported_actions or [])
        ]

    def is_model_installed(self, model_name: str) -> bool:
        wanted = model_name.removeprefix("models/")
        return any(m["id"] == wanted for m in self.list_models())

    # --- Tool calling --------------------------------------------------------

    def format_tools(self, tools):
        """Convert OpenAI-style tool defs into a single Gemini `Tool` wrapping
        one `FunctionDeclaration` per tool. The JSON Schema is passed through
        `parameters_json_schema`, which accepts standard JSON Schema as-is."""
        if not tools:
            return None

        declarations = [
            types.FunctionDeclaration(
                name=tool["function"]["name"],
                description=tool["function"].get("description", ""),
                parameters_json_schema=tool["function"].get("parameters"),
            )
            for tool in tools
        ]
        return [types.Tool(function_declarations=declarations)]

    def parse_tool_calls(self, response):
        function_calls = response.function_calls or []
        return [
            {
                "id": fc.id,
                "name": fc.name,
                "arguments": dict(fc.args or {}),
            }
            for fc in function_calls
        ]

    def add_usage(self, usage, response):
        meta = getattr(response, "usage_metadata", None)
        if meta:
            usage.add(
                getattr(meta, "prompt_token_count", 0) or 0,
                getattr(meta, "candidates_token_count", 0) or 0,
            )

    def build_assistant_message(self, response):
        # Preserve the model turn verbatim (function-call parts and any text) so
        # the next request sees its own prior calls.
        candidate = response.candidates[0]
        return types.Content(
            role="model",
            parts=candidate.content.parts,
        )

    def build_tool_result_message(self, tool_call, result):
        # Gemini expects the tool output wrapped as a JSON object; a bare list or
        # scalar would be rejected, so wrap non-dict results under "result".
        response = result if isinstance(result, dict) else {"result": result}
        return types.Content(
            role="user",
            parts=[
                types.Part.from_function_response(
                    name=tool_call["name"],
                    response=response,
                )
            ],
        )

    def iter_stream(self, stream):
        # Unlike Ollama, Gemini has no per-chunk "done" flag — the stream simply
        # ends, and the final chunk carries usage_metadata. So we relay text as
        # it arrives and synthesize a single terminal event once the loop ends.
        last = None

        for chunk in stream:
            last = chunk

            # Walk the parts ourselves rather than using `chunk.text`: it raises
            # when a chunk has no text part (function call / safety block) and it
            # can't tell a thought summary (part.thought) from the real answer.
            content_text = None
            thinking_text = None

            candidates = getattr(chunk, "candidates", None) or []
            if candidates:
                parts = getattr(candidates[0].content, "parts", None) or []
                for part in parts:
                    text = getattr(part, "text", None)
                    if not text:
                        continue
                    if getattr(part, "thought", False):
                        thinking_text = (thinking_text or "") + text
                    else:
                        content_text = (content_text or "") + text

            yield {
                "content": content_text,
                "thinking": thinking_text,
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
