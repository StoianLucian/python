from agents.base import SubAgent
from agents.blackboard import BlackBoard
from agents.config import EVALUATE_INSTRUCTION


class EvaluatorAgent(SubAgent):
    """Decides the control verdict: CONTINUE / CLARIFY / DONE (parsed by the
    orchestrator via substring match, robust to small-model chatter)."""
    role = "evaluator"

    def system_prompt(self, bb: BlackBoard) -> str:
        return EVALUATE_INSTRUCTION

    def user_prompt(self, bb: BlackBoard, **kw) -> str:
        return bb.evaluator_view()
