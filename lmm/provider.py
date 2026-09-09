from abc import ABC, abstractmethod

class LMMProvider(ABC):
    @abstractmethod
    def chat(self ,model, messages, stream= False, tools = None, options=None, thinking= False):
        pass

    @abstractmethod
    def list_models(self):
        """Return available chat models as [{"name": str, "id": str}, ...]."""
        pass

    @abstractmethod
    def is_model_installed(self, model_name: str) -> bool:
        """Return True if the model is available for use with this provider."""
        pass

    @abstractmethod
    def iter_stream(self, stream):
        """Normalize a provider streaming response into common events:

            {"content": str | None,
             "thinking": str | None,
             "done": bool,
             "usage": {"input": int, "output": int} | None}

        Exactly one terminal event with ``done=True`` is emitted last; ``usage``
        is populated on that event when the provider reports token counts.
        """
        pass

    # --- Tool calling ----------------------------------------------------
    # The router speaks one generic tool-calling protocol and lets each
    # provider translate to/from its own wire format, so the tool loop stays
    # provider-agnostic. Tools are handed in as OpenAI-style definitions:
    #   {"type": "function",
    #    "function": {"name": str, "description": str, "parameters": <schema>}}

    @abstractmethod
    def format_tools(self, tools):
        """Convert generic OpenAI-style tool definitions into this provider's
        native tool format. Return None when there are no tools."""
        pass

    @abstractmethod
    def parse_tool_calls(self, response):
        """Return tool calls from a non-streaming response, normalized as
        [{"id": str | None, "name": str, "arguments": dict}, ...] (empty when
        the model requested none)."""
        pass

    @abstractmethod
    def add_usage(self, usage, response):
        """Accumulate token usage from a non-streaming response into `usage`
        (a lmm.usage.TokenUsage)."""
        pass

    @abstractmethod
    def build_assistant_message(self, response):
        """Return the assistant turn (in this provider's native message format)
        to append to the conversation so its tool calls are preserved in
        history for the next iteration."""
        pass

    @abstractmethod
    def build_tool_result_message(self, tool_call, result):
        """Return the tool-result turn (native message format) for one executed
        tool call. `tool_call` is a dict from `parse_tool_calls`; `result` is
        the JSON-serializable tool output."""
        pass
