import json

from .provider import LMMProvider


class MLXProvider(LMMProvider):
    """Talks to a local ``mlx_lm.server`` over its OpenAI-compatible HTTP API.

    MLX-LM (Apple-Silicon only) ships an OpenAI-compatible server; start it
    before pointing this provider at it, e.g.::

        mlx_lm.server --model mlx-community/Qwen2.5-7B-Instruct-4bit --port 8080

    Because the server speaks the OpenAI chat-completions wire format, the
    router's generic OpenAI-style tool defs pass through almost unchanged
    (`format_tools`), and every message this provider builds is a plain
    OpenAI-shaped dict — the same family the router already produces for Ollama.

    The ``openai`` SDK is imported lazily so the rest of the app (and the Linux
    Docker build) stays importable without it; only constructing this provider
    requires the package.
    """

    def __init__(self, base_url: str, api_key: str = "not-needed"):
        try:
            from openai import OpenAI
        except ImportError as e:  # pragma: no cover - import-time guard
            raise RuntimeError(
                "The 'openai' package is required for the MLX provider. "
                "Install it with `pip install openai`."
            ) from e

        # mlx_lm.server ignores the key, but the OpenAI client demands a truthy
        # one, so we pass a placeholder.
        self.client = OpenAI(base_url=base_url, api_key=api_key or "not-needed")

    def chat(
        self,
        model,
        messages,
        stream=False,
        tools=None,
        options=None,
        thinking=False,
        format=None,
    ):
        kwargs = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }

        # `options` carries generic sampling knobs (e.g. {"temperature": 0}).
        # The OpenAI API takes these as top-level params and ignores ones it
        # doesn't recognize (such as Ollama's num_ctx), so spreading is safe.
        if options:
            kwargs.update(options)

        if tools:
            kwargs["tools"] = tools

        if format == "json":
            # The router uses the generic "json"; the OpenAI API wants a
            # response_format object.
            kwargs["response_format"] = {"type": "json_object"}

        if stream:
            # Ask the server to append a final usage-only chunk so streaming
            # turns can still report token counts.
            kwargs["stream_options"] = {"include_usage": True}

        # `thinking` has no portable switch in the OpenAI chat API; models that
        # reason do so on their own and surface it via `reasoning_content`
        # (handled in parse_thinking / the stream readers), so there's nothing
        # to toggle on the request.
        return self.client.chat.completions.create(**kwargs)

    def list_models(self):
        result = []
        for m in self.client.models.list().data:
            model_id = m.id
            if "embed" in model_id.lower():
                continue
            result.append(
                {
                    "name": model_id,
                    "id": model_id,
                    # The server's model listing carries no capability flags, so
                    # we report conservatively; flip these per-model if you wire
                    # up a known-capabilities map or add mlx-vlm for vision.
                    "thinking": False,
                    "vision": False,
                }
            )
        return result

    def is_model_installed(self, model_name: str) -> bool:
        return any(m["id"] == model_name for m in self.list_models())

    # --- Tool calling ----------------------------------------------------
    # The server already speaks the OpenAI-style tool format the router
    # produces, so tool defs pass straight through.

    def format_tools(self, tools):
        return tools or None

    def parse_tool_calls(self, response):
        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None) or []
        return [
            {
                "id": tc.id,
                "name": tc.function.name,
                "arguments": self._parse_args(tc.function.arguments),
            }
            for tc in tool_calls
        ]

    def parse_thinking(self, response):
        # DeepSeek-style reasoning models (and mlx_lm.server when serving one)
        # expose the thought summary on `reasoning_content`; it's absent/None
        # for plain models.
        message = response.choices[0].message
        return getattr(message, "reasoning_content", None) or None

    def add_usage(self, usage, response):
        meta = getattr(response, "usage", None)
        if meta:
            usage.add(
                getattr(meta, "prompt_tokens", 0) or 0,
                getattr(meta, "completion_tokens", 0) or 0,
            )

    def build_assistant_message(self, response):
        # Preserve the model turn (text + any tool calls) in OpenAI's native
        # shape so the next request sees its own prior calls.
        message = response.choices[0].message
        out = {"role": "assistant", "content": message.content or ""}
        if getattr(message, "tool_calls", None):
            out["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        # Keep arguments as the raw JSON string the API returned;
                        # that's what the chat endpoint expects on the way back.
                        "arguments": tc.function.arguments or "{}",
                    },
                }
                for tc in message.tool_calls
            ]
        return out

    def build_tool_result_message(self, tool_call, result):
        # OpenAI pairs a tool result to its call via tool_call_id.
        return {
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": json.dumps(result),
        }

    def iter_stream(self, stream):
        # OpenAI streams have no per-chunk "done" flag — the stream ends and, with
        # stream_options.include_usage, a final choices-less chunk carries usage.
        usage = None

        for chunk in stream:
            if getattr(chunk, "usage", None):
                usage = {
                    "input": chunk.usage.prompt_tokens or 0,
                    "output": chunk.usage.completion_tokens or 0,
                }

            choices = chunk.choices or []
            if not choices:
                continue

            delta = choices[0].delta
            content = getattr(delta, "content", None)
            thinking = getattr(delta, "reasoning_content", None)

            if content or thinking:
                yield {
                    "content": content,
                    "thinking": thinking,
                    "done": False,
                    "usage": None,
                }

        yield {"content": None, "thinking": None, "done": True, "usage": usage}

    def stream_turn(self, stream):
        # Relay content/thinking deltas live while accumulating the full text and
        # reassembling tool calls, which OpenAI streams as per-index fragments
        # (id + name arrive early, the JSON arguments string arrives in pieces).
        content_acc = ""
        tool_frags = {}  # index -> {"id", "name", "arguments" (str so far)}
        usage = None

        for chunk in stream:
            if getattr(chunk, "usage", None):
                usage = {
                    "input": chunk.usage.prompt_tokens or 0,
                    "output": chunk.usage.completion_tokens or 0,
                }

            choices = chunk.choices or []
            if not choices:
                continue

            delta = choices[0].delta

            content = getattr(delta, "content", None)
            thinking = getattr(delta, "reasoning_content", None)

            if content:
                content_acc += content

            if content or thinking:
                yield {
                    "content": content,
                    "thinking": thinking,
                    "done": False,
                    "tool_calls": None,
                    "assistant_message": None,
                    "usage": None,
                }

            for tc in getattr(delta, "tool_calls", None) or []:
                slot = tool_frags.setdefault(
                    tc.index, {"id": None, "name": "", "arguments": ""}
                )
                if tc.id:
                    slot["id"] = tc.id
                fn = getattr(tc, "function", None)
                if fn:
                    if fn.name:
                        slot["name"] += fn.name
                    if fn.arguments:
                        slot["arguments"] += fn.arguments

        tool_calls = []
        native_tool_calls = []
        for index in sorted(tool_frags):
            slot = tool_frags[index]
            args_str = slot["arguments"] or "{}"
            tool_calls.append(
                {
                    "id": slot["id"],
                    "name": slot["name"],
                    "arguments": self._parse_args(args_str),
                }
            )
            native_tool_calls.append(
                {
                    "id": slot["id"],
                    "type": "function",
                    "function": {"name": slot["name"], "arguments": args_str},
                }
            )

        assistant_message = {"role": "assistant", "content": content_acc}
        if native_tool_calls:
            assistant_message["tool_calls"] = native_tool_calls

        yield {
            "content": None,
            "thinking": None,
            "done": True,
            "tool_calls": tool_calls,
            "assistant_message": assistant_message,
            "usage": usage,
        }

    @staticmethod
    def _parse_args(arguments):
        """Decode a tool call's JSON arguments string into a dict, tolerating the
        empty/malformed output a small local model can occasionally emit."""
        try:
            return json.loads(arguments or "{}")
        except json.JSONDecodeError:
            return {}
