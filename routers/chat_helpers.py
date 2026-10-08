"""Shared, dependency-light building blocks for the chat endpoints.

These were originally defined inline in `routers/ai_chat.py`. They were extracted
here so the multi-agent path (`agents/`) can reuse them without importing
`ai_chat` (which would create an import cycle `ai_chat -> agents -> ai_chat`).
This module imports nothing from `ai_chat` or `agents`, so it stays cycle-free.
"""

from typing import Optional
import copy
import json

from pydantic import BaseModel


# --- Request models --------------------------------------------------------

class Message(BaseModel):
    role: str
    content: str
    images: Optional[list[str]] = None


class ChatRequestTest(BaseModel):
    messages: list[Message]
    model: str
    provider: Optional[str] = None
    thinking: Optional[bool] = False
    # The chat conversation (`chat_sessions.id`) this request belongs to, when
    # the client has one. Injected server-side into session-scoped tools (see
    # `SESSION_SCOPED_TOOLS`) so the model can recall earlier turns of THIS
    # conversation without us having to re-send them every request.
    session_id: Optional[int] = None


# --- Tool / sampling config ------------------------------------------------

# Tools whose `created_by` must be filled from the authenticated user, never
# from the LLM. The argument is stripped from the tool schema shown to the model
# (see `sanitize_tool_schema`) and injected server-side before the call.
USER_SCOPED_TOOLS = {
    "add_food_entry",
    "get_daily_totals_tool",
    "add_exercise_entry",
    "get_exercise_daily_totals",
    "get_conversation_history",
}

# Tools whose `session_id` must be filled from the current conversation, never
# from the LLM. Like `created_by`, the argument is stripped from the schema the
# model sees and injected server-side from the request's `session_id`.
SESSION_SCOPED_TOOLS = {
    "get_conversation_history",
}


def inject_scoped_args(tool_name: str, tool_args: dict, user, session_id=None) -> dict:
    """Return `tool_args` with the server-controlled scoping fields added for
    this tool: `created_by` for user-scoped tools, `session_id` for
    session-scoped ones. Never lets the model supply these itself."""
    args = dict(tool_args)
    if tool_name in USER_SCOPED_TOOLS and user is not None:
        args["created_by"] = user["user_id"]
    if tool_name in SESSION_SCOPED_TOOLS and session_id is not None:
        args["session_id"] = session_id
    return args

# Sampling options for every model call. Temperature 0 for deterministic,
# reproducible answers. Note: Qwen3 warns that greedy decoding can cause
# repetition loops — if that surfaces, the "Tool loop detected" guard will catch
# it, but consider nudging temperature back up for that model.
SAMPLING_OPTIONS = {"temperature": 0}


# Arguments the server fills in itself (never the model): the per-user and
# per-conversation scoping fields. Stripped from every tool schema shown to the
# model so it neither sees nor fills them.
_SERVER_INJECTED_ARGS = ("created_by", "session_id")


def sanitize_tool_schema(schema: dict) -> dict:
    """Return a copy of an MCP tool's input schema with the server-injected
    scoping arguments (`created_by`, `session_id`) removed, so the model neither
    sees nor fills them."""
    schema = copy.deepcopy(schema or {})

    properties = schema.get("properties")
    if isinstance(properties, dict):
        for arg in _SERVER_INJECTED_ARGS:
            properties.pop(arg, None)

    required = schema.get("required")
    if isinstance(required, list):
        schema["required"] = [
            r for r in required if r not in _SERVER_INJECTED_ARGS]

    return schema


def format_provider_error(exc: Exception) -> str:
    """Turn a provider/SDK exception into a short, user-facing message.

    Duck-types on the attributes google-genai (APIError: .code/.message) and
    Ollama (ResponseError: .status_code/.error) expose, so it stays
    provider-agnostic without importing either SDK's error types."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)

    if code == 429:
        return ("The model is rate-limited right now (quota exceeded). "
                "Please wait a moment and try again.")
    if code == 404:
        return ("The selected model isn't available. "
                "Please pick a different model.")
    if code in (401, 403):
        return ("The AI provider rejected the request. "
                "Check the API key or your access to this model.")

    message = getattr(exc, "message", None) or getattr(
        exc, "error", None) or str(exc)
    # Keep it to the first line so we never dump a stack/JSON blob at the user.
    lines = [line for line in str(
        message).strip().splitlines() if line.strip()]
    if lines:
        return f"The AI provider returned an error: {lines[0]}"
    return "Something went wrong contacting the AI provider. Please try again."


def to_provider_messages(messages: list[Message]) -> list[dict]:
    """Convert incoming chat messages into the provider-agnostic dict format the
    providers consume. `images` is a list of base64 strings (no data-URL prefix).

    Only the single most recent image across the whole history is forwarded:
    images are expensive in tokens (a vision model expands one into hundreds),
    so carrying every past attachment would blow the model's context window.
    Earlier images are dropped and text-only turns are passed through unchanged."""
    # Index of the last message that carries any image; -1 when there are none.
    last_image_idx = next(
        (i for i in range(len(messages) - 1, -1, -1) if messages[i].images),
        -1,
    )

    result = []
    for i, m in enumerate(messages):
        msg = {"role": m.role, "content": m.content}
        if i == last_image_idx:
            # Keep only the last image on that message, in case it had several.
            msg["images"] = [m.images[-1]]
        result.append(msg)
    return result


def error_event(message: str) -> str:
    """NDJSON line the frontend renders as an error bubble. The content follows
    the same JSON-array contract the model uses, with a single `error` object,
    so ChatMessage displays it as an alert."""
    body = json.dumps([{"type": "error", "text": message}])
    return json.dumps({"content": body, "thinking": None, "done": True}) + "\n"


def thinking_step(number: int, label: str) -> str:
    """NDJSON line for one numbered progress step, streamed on the `thinking`
    channel (which the client accumulates and displays). Instead of surfacing
    the model's raw, verbose chain-of-thought, we send a concise summary of what
    the agent is doing — e.g. "1. Evaluating your request". Not part of the
    final answer content."""
    return json.dumps({"thinking": f"{number}. {label}\n", "done": False}) + "\n"


def timing_line(seconds: float, name: Optional[str] = None) -> str:
    """NDJSON line noting how long the preceding step took, streamed on the
    `thinking` channel as a sub-line under it. Emitted once the work finishes,
    since each step label is sent before its work for live feedback. Pass `name`
    to attribute the time to a specific tool."""
    label = f"{name} took {seconds:.2f}s" if name else f"took {seconds:.2f}s"
    return json.dumps({"thinking": f"   ↳ {label}\n", "done": False}) + "\n"


def tool_step_label(tool_call: dict) -> str:
    """Build the user-facing status line for one tool call from the tool name
    alone, so we never leak the (possibly sensitive) tool arguments to the UI.

    The label is derived from the tool name (snake_case → spaced words), so it
    works for every available tool without hardcoding per-tool strings."""
    name = tool_call.get("name", "")
    if not name:
        return "Running tool"
    return f"Running {name.replace('_', ' ').strip()}"
