from agents.base import SubAgent
from agents.blackboard import BlackBoard
from agents.config import OBSERVER_PROMPT


class ObserverAgent(SubAgent):
    """Interprets the just-executed tool results into a concise observation. The
    one role that sees raw tool JSON — and only for the newest calls."""
    role = "observer"

    def system_prompt(self, bb: BlackBoard) -> str:
        return OBSERVER_PROMPT

    def user_prompt(self, bb: BlackBoard, *, new_calls=None, **kw) -> str:
        return bb.observer_view(new_calls or [])
