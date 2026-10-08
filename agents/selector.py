from agents.base import SubAgent
from agents.blackboard import BlackBoard
from agents.config import SELECTOR_PROMPT


class SelectorAgent(SubAgent):
    """The only agent given tool definitions; it emits the tool calls for the
    current objective (the orchestrator executes them)."""
    role = "selector"
    gives_tools = True

    def system_prompt(self, bb: BlackBoard) -> str:
        return SELECTOR_PROMPT

    def user_prompt(self, bb: BlackBoard, **kw) -> str:
        return bb.selector_view()
