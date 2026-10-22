"""Prompt(s) for the chat path.

The Orchestrator runs a single tool-calling loop. The gathered tool results are
turned into the typed JSON answer by one focused formatting call, which uses
`agent_prompt` (the base contract, in `prompts/prompts.py`) plus the instruction
below.
"""

ANSWER_INSTRUCTION = (
    "Write the final answer for the user as a single valid JSON array. Follow the "
    "response format and any tool output-format contract shown above exactly — "
    "match their object SHAPE, but build every value from the raw tool results "
    "provided. Do not mention these steps and do not call any tools.\n"
    "Sources are REQUIRED, not optional: whenever a tool returned source-bearing "
    "results (for example `search_documents` passages carrying `source_id` and "
    "`page_number`), you MUST include the corresponding source object (e.g. a "
    "`popover`, exactly as the tool contract defines it) for EVERY document that "
    "supports your answer. Include one per supporting document, copy `source_id`, "
    "`page_number`, and any `content` VERBATIM from the tool result, and never "
    "invent them. Only omit a source if its document did not contribute to the "
    "answer."
)
