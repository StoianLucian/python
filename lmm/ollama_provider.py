import json

from ollama import Client, ResponseError
from .provider import LMMProvider

DEFAULT_NUM_CTX = 8192


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
        format=None
    ):
        # Ensure a context window large enough for image/long-history requests,
        # while letting an explicit num_ctx from the caller win.
        merged_options = {"num_ctx": DEFAULT_NUM_CTX, **(options or {})}

        kwargs = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": merged_options,
            "think": thinking,
            "format": format
        }

        if tools:
            kwargs["tools"] = tools

        return self.client.chat(**kwargs)

    def list_models(self):
        models = self.client.list()

        result = []
        for m in models["models"]:
            model_name = m["model"]
            if "embed" in model_name.lower():
                continue

            capabilities = self._capabilities(model_name)
            result.append(
                {
                    "name": model_name,
                    "id": model_name,
                    "thinking": "thinking" in capabilities,
                    "vision": "vision" in capabilities,
                }
            )

        return result

    def _capabilities(self, model_name: str) -> list:

        try:
            return self.client.show(model_name).capabilities or []
        except ResponseError as e:
            print(e)
            return []

    def is_model_installed(self, model_name: str) -> bool:
        try:
            self.client.show(model_name)
            return True
        except ResponseError as e:
            print(e)
            return False

    # --- Tool calling ----------------------------------------------------
    # Ollama's chat API already speaks the OpenAI-style tool format the router
    # produces, so tool defs pass straight through.

    def format_tools(self, tools):
        return tools or None

    def parse_tool_calls(self, response):
        tool_calls = getattr(response.message, "tool_calls", None)
        if not tool_calls:
            return []
        return [
            {
                "id": None,
                "name": tc.function.name,
                "arguments": tc.function.arguments or {},
            }
            for tc in tool_calls
        ]

    def parse_thinking(self, response):
        # `think=True` makes Ollama put the reasoning on message.thinking; it's
        # absent/None otherwise.
        return getattr(response.message, "thinking", None) or None

    def add_usage(self, usage, response):
        usage.add_ollama(response)

    def build_assistant_message(self, response):
        message = {
            "role": "assistant",
            "content": response.message.content or "",
        }
        if response.message.tool_calls:
            message["tool_calls"] = [
                tc.model_dump() for tc in response.message.tool_calls
            ]
        return message

    def build_tool_result_message(self, tool_call, result):
        return {
            "role": "tool",
            "name": tool_call["name"],
            "content": json.dumps(result),
        }

    def iter_stream(self, stream):
        for chunk in stream:
            message = chunk.get("message", {})
            done = bool(chunk.get("done"))

            usage = None
            if done:
                # Ollama puts the token counts on the final (done) chunk.
                usage = {
                    "input": chunk.get("prompt_eval_count") or 0,
                    "output": chunk.get("eval_count") or 0,
                }

            yield {
                "content": message.get("content"),
                "thinking": message.get("thinking"),
                "done": done,
                "usage": usage,
            }

    def stream_turn(self, stream):
        # Relay content/thinking deltas live while accumulating the full text and
        # any tool calls (Ollama delivers tool_calls on a chunk's message, with
        # the token counts on the final `done` chunk).
        content_acc = ""
        tool_calls_raw = []
        last = None

        for chunk in stream:
            last = chunk
            message = chunk.get("message", {})

            content = message.get("content")
            thinking = message.get("thinking")

            tcs = message.get("tool_calls")
            if tcs:
                tool_calls_raw.extend(tcs)

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

        usage = {
            "input": (last.get("prompt_eval_count") if last is not None else 0) or 0,
            "output": (last.get("eval_count") if last is not None else 0) or 0,
        }

        tool_calls = [
            {
                "id": None,
                "name": tc.function.name,
                "arguments": tc.function.arguments or {},
            }
            for tc in tool_calls_raw
        ]

        assistant_message = {"role": "assistant", "content": content_acc}
        if tool_calls_raw:
            assistant_message["tool_calls"] = [
                tc.model_dump() for tc in tool_calls_raw
            ]

        yield {
            "content": None,
            "thinking": None,
            "done": True,
            "tool_calls": tool_calls,
            "assistant_message": assistant_message,
            "usage": usage,
        }
