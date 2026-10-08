from agents.base import SubAgent
from agents.blackboard import BlackBoard
from agents.config import PLANNER_PROMPT


class PlannerAgent(SubAgent):
    """Decides the single next objective from the request + what's gathered."""
    role = "planner"

    def system_prompt(self, bb: BlackBoard) -> str:
        return PLANNER_PROMPT

    def user_prompt(self, bb: BlackBoard, **kw) -> str:
        return bb.planner_view()
