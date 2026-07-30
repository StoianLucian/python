from abc import ABC, abstractmethod
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

    @abstractmethod
    def register(self, mcp):
        """Register MCP tools."""

    def prompt(self) -> str:
        path = Path(__file__).parent / self.name / "prompt.md"

        if path.exists():
            return path.read_text()

        return ""

    def examples(self) -> str:
        path = Path(__file__).parent / self.name / "examples.md"

        if path.exists():
            return path.read_text()

        return ""