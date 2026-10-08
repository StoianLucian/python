"""Role prompts and per-role model resolution for the v3 multi-agent path.

Prompts for roles that don't exist in v1/v2 (Planner, Selector, Observer) are
defined here. The Evaluator/Clarifier wording mirrors v1's instructions but is
kept here so `agents/` stays self-contained (importing them from `routers.ai_chat`
would create an import cycle). The Answerer additionally uses `agent_prompt`.
"""

import os

PLANNER_PROMPT = (
    "You are the Planner in a multi-agent assistant. Given the user's request and "
    "what has been gathered so far, state the SINGLE next objective that moves "
    "toward a complete answer, in one short sentence. If everything needed is "
    "already gathered, say so plainly. Do not call tools and do not write the "
    "final answer."
)

SELECTOR_PROMPT = (
    "You are the Tool Selector in a multi-agent assistant. Given the current "
    "objective and the available tools, call exactly the tool(s) needed to achieve "
    "that objective. If no tool is needed, do not call any. Do not write prose or "
    "the final answer — your only output is tool calls when appropriate."
)

OBSERVER_PROMPT = (
    "You are the Observer in a multi-agent assistant. Read the raw tool results "
    "below and summarize, in 1-3 sentences, only the facts in them that are "
    "relevant to the user's request. State facts only — do not add citations, do "
    "not answer the user, do not call tools, and do not invent anything that is "
    "not present in the results."
)

# One-word control verdict (same contract as v1's EVALUATE step).
EVALUATE_INSTRUCTION = (
    "Evaluate the current state. Reply with EXACTLY ONE word on its own:\n"
    "- CONTINUE — more work/tool calls are needed before you can answer.\n"
    "- CLARIFY — you cannot proceed without more information from the user.\n"
    "- DONE — you now have everything needed to write the final answer.\n"
    "Reply with only that single word."
)

CLARIFY_INSTRUCTION = (
    "You need more information from the user. Ask ONE concise clarifying question "
    "as a single valid JSON array following the response format. Do not answer "
    "the original question and do not call any tools."
)

ANSWER_INSTRUCTION = (
    "Write the final answer for the user as a single valid JSON array. Follow the "
    "response format and any tool output-format contract shown above exactly — "
    "match their object SHAPE, but build every value from the observations and raw "
    "tool results provided. Do not mention these steps and do not call any tools."
)


def model_for(role: str, request_model: str) -> str:
    """Resolve the model for a sub-agent role.

    Priority: a role-specific env var `V3_<ROLE>_MODEL`, then the shared
    `ROUTER_MODEL`, then the model the client requested. With no env vars set,
    every role uses the request model, so v3 runs out of the box. This
    generalizes the existing `ROUTER_MODEL` pattern used by v2's router."""
    return (
        os.getenv(f"V3_{role.upper()}_MODEL")
        or os.getenv("ROUTER_MODEL")
        or request_model
    )
