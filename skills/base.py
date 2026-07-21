from abc import ABC, abstractmethod
from pathlib import Path


class Skill(ABC):

    name: str
    description: str
    tools: list[str]

    @abstractmethod
    def register(self, mcp):
        """Register MCP tools."""

    @abstractmethod
    def prompt(self) -> str:
        """Return the prompt for this skill."""
        path = Path(__file__).parent / self.name / "prompt.md"
        
        if path.exists():
            return path.read_text()
        
        return ""
        
    @abstractmethod
    def examples(self) -> str:
        """Return examples for this skill."""
        
        path = Path(__file__).parent / self.name / "examples.md"
        
        if path.exists():
            return path.read_text()
        
        return ""
