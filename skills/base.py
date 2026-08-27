from abc import ABC
from pathlib import Path
from dataclasses import dataclass


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
        path = Path(__file__).parent / self.name

        if not path.is_dir():
            raise FileNotFoundError(
                f"{type(self).__name__}: no skill directory at '{path}'. "
                f"The folder must be named after the skill's name ('{self.name}')."
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