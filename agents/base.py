"""The SubAgent base: all the provider-call / streaming / usage plumbing, so each
concrete role is just a system prompt + a blackboard projection."""

import json
from abc import ABC, abstractmethod

from lmm.usage import TokenUsage
from routers.chat_helpers import SAMPLING_OPTIONS
from agents.blackboard import BlackBoard


def ndjson(*, content=None, thinking=None, done=False) -> str:
    """One NDJSON stream line in the same wire shape v1/v2 emit."""
    return json.dumps(
        {"content": content, "thinking": thinking, "done": done}) + "\n"


class SubAgent(ABC):
    """One specialized agent. Each turn is a fresh TWO-message conversation
    (role system prompt + scoped blackboard view) — the structural contrast with
    v1/v2's single growing `messages` list.

    Flags set by subclasses:
      emits_content   — stream the model's text to the content channel (answer
                        stages only); others produce step labels via the
                        orchestrator and stay silent on content.
      use_json_format — enforce JSON output (answer stages only; must be
                        tool-free, since format="json" can't combine with tools
                        on all providers).
      gives_tools     — receive the native tool defs (Selector only).
    """

    role: str = "agent"
    emits_content: bool = False
    use_json_format: bool = False
    gives_tools: bool = False

    def __init__(self, provider, model: str, usage: TokenUsage):
        self.provider = provider
        self.model = model          # resolved per-role (see config.model_for)
        self.usage = usage          # shared across all agents in one request

    @abstractmethod
    def system_prompt(self, bb: BlackBoard) -> str:
        ...

    @abstractmethod
    def user_prompt(self, bb: BlackBoard, **kw) -> str:
        ...

    def build_messages(self, bb: BlackBoard, **kw) -> list[dict]:
        return [
            {"role": "system", "content": self.system_prompt(bb)},
            {"role": "user", "content": self.user_prompt(bb, **kw)},
        ]

    async def run(self, bb: BlackBoard, out: dict, *, native_tools=None, **kw):
        """Run one turn. Streams NDJSON content lines (only for answer stages),
        accumulates the turn's text / tool calls into `out`, and bills the shared
        usage. Returns nothing; results are read from `out` by the caller."""
        messages = self.build_messages(bb, **kw)
        stream = self.provider.chat(
            self.model, messages, True,
            tools=(native_tools if self.gives_tools else None),
            options=SAMPLING_OPTIONS,
            thinking=False,
            format=("json" if self.use_json_format else None),
        )

        text = ""
        tool_calls = []
        assistant_message = None
        for ev in self.provider.stream_turn(stream):
            if self.emits_content and (ev["content"] or ev["thinking"]):
                yield ndjson(content=ev["content"], thinking=ev["thinking"])
            if ev["content"]:
                text += ev["content"]
            if ev["done"]:
                tool_calls = ev["tool_calls"] or []
                assistant_message = ev["assistant_message"]
                if ev["usage"]:
                    self.usage.add(ev["usage"]["input"], ev["usage"]["output"])

        out["text"] = text
        out["tool_calls"] = tool_calls
        out["assistant_message"] = assistant_message
