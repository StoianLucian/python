import inspect
from abc import ABC
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


class Skill(ABC):
    REQUIRED = ("name", "description", "tools", "trigger")
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        for attr in cls.REQUIRED:
            if attr not in cls.__dict__:
                raise TypeError(
                    f"{cls.__name__} must define '{attr}'"
                )

    name: str
    description: str
    tools: list[str]
    trigger: list[str]
    keywords: list[str]

    def register(self, mcp):
        """Register the skill's MCP tools.

        Override this when a skill owns tool implementations. Skills that only
        reuse tools already registered by another skill (declared in `tools`)
        can leave this as the default no-op — registering again would create
        duplicate tools on the MCP server.
        """

    def directory(self) -> Path:
        # Resolve the skill's own folder from where its subclass is defined
        # (skills/<folder>/skill.py) rather than from ``self.name``. The
        # human-facing name (e.g. "calories", "email") intentionally differs
        # from the folder name (add_calories, send_email), so coupling the two
        # would break skill lookups.
        path = Path(inspect.getfile(type(self))).resolve().parent

        if not path.is_dir():
            raise FileNotFoundError(
                f"{type(self).__name__}: no skill directory at '{path}'."
            )

        return path

    def prompt(self) -> str:
        path = self.directory() / "prompt.md"

        if path.exists():
            return path.read_text()

        return ""

    def examples(self) -> str:
        path = self.directory() / "examples.md"

        if path.exists():
            return path.read_text()

        return ""

    def render_response(self, tool_history: list[dict]) -> Optional[list[dict]]:
        """Optionally build the final response objects deterministically from
        the tool results, bypassing the answer-generation model call.

        Return a list of response objects (the same JSON-array shape the model
        would emit) to short-circuit generation, or ``None`` to let the model
        produce the answer. Use this when the tool result already contains the
        finished answer and re-synthesizing it through a small local model is
        unreliable.
        """
        return None