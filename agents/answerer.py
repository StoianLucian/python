from prompts.prompts import agent_prompt

from agents.base import SubAgent
from agents.blackboard import BlackBoard
from agents.config import ANSWER_INSTRUCTION, CLARIFY_INSTRUCTION


class AnswererAgent(SubAgent):
    """Composes the final JSON answer. System prompt = the shared agent_prompt
    (base JSON contract) + the skill instructions/output contract on the
    blackboard; user prompt = observations + verbatim raw results. Tool-free and
    JSON-enforced."""
    role = "answerer"
    emits_content = True
    use_json_format = True

    def system_prompt(self, bb: BlackBoard) -> str:
        parts = [agent_prompt]
        if bb.skill_prompt:
            parts.append("## Skill instructions\n" + bb.skill_prompt)
        if bb.output_contract:
            parts.append(
                "## Output-format contract (match the object SHAPE EXACTLY)\n"
                + bb.output_contract)
        parts.append(ANSWER_INSTRUCTION)
        return "\n\n".join(parts)

    def user_prompt(self, bb: BlackBoard, **kw) -> str:
        return bb.answerer_view()


class ClarifierAgent(SubAgent):
    """Asks the user ONE clarifying question as JSON, ending the turn."""
    role = "clarifier"
    emits_content = True
    use_json_format = True

    def system_prompt(self, bb: BlackBoard) -> str:
        return agent_prompt + "\n\n" + CLARIFY_INSTRUCTION

    def user_prompt(self, bb: BlackBoard, **kw) -> str:
        return bb.clarifier_view()
