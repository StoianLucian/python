from typing import Optional

from fastapi import APIRouter, Depends
from lmm.factory import get_lmm_provider
from lmm.usage import TokenUsage
from repositories.ai_chat_repository import is_model_installed, return_available_models
from prompts.prompts import tool_calling_prompt, tool_phase_prompt, test_prompt
from schemas import *
from fastapi.responses import StreamingResponse
import copy
import json
from fastmcp import Client
from import_folder.mcp_server import mcp as mcp_server

from repositories import *
from tools.cache.mcp_tools_cache import MCPToolsCache
from tools.helpers import find_skill, strip_trigger

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


class ChatRequest(BaseModel):
    prompt: str
    model: str


class Message(BaseModel):
    role: str
    content: str
    images: Optional[list[str]] = None


class ChatRequestTest(BaseModel):
    messages: list[Message]
    model: str
    provider: Optional[str] = None
    thinking: Optional[bool] = False


# Connect to the in-process FastMCP server directly (in-memory transport).
# Passing the server instance avoids an HTTP round-trip to ourselves, so it
# works regardless of the port uvicorn binds to (e.g. Render's $PORT) and needs
# no separate MCP server process.
mcp = Client(mcp_server)


# Tools whose `created_by` must be filled from the authenticated user, never
# from the LLM. The argument is stripped from the tool schema shown to the model
# (see `sanitize_tool_schema`) and injected server-side before the call.
USER_SCOPED_TOOLS = {
    "add_food_entry",
    "get_daily_totals_tool",
    "add_exercise_entry",
    "get_exercise_daily_totals",
}

# Sampling options for every model call. Qwen3 explicitly warns against greedy
# decoding (temperature 0) — it can cause repetition loops that would trip the
# "Tool loop detected" guard — so we use its recommended non-thinking settings.
SAMPLING_OPTIONS = {"temperature": 0.7, "top_p": 0.8, "top_k": 20}


def sanitize_tool_schema(schema: dict) -> dict:
    """Return a copy of an MCP tool's input schema with the server-injected
    `created_by` argument removed, so the model neither sees nor fills it."""
    schema = copy.deepcopy(schema or {})

    properties = schema.get("properties")
    if isinstance(properties, dict):
        properties.pop("created_by", None)

    required = schema.get("required")
    if isinstance(required, list):
        schema["required"] = [r for r in required if r != "created_by"]

    return schema


test_prompt = """You are a JSON-only assistant.

Every response MUST be a valid JSON array.

The array may contain one or more objects. These base object types are always
available:

Text:
{
  "type": "text",
  "text": "<string>"
}

Error:
{
  "type": "error",
  "text": "<string>"
}

Additional object types may be defined by the skill instructions later in this
conversation. When skill instructions define an object type, that type is
allowed and you MUST use it exactly as shown in its examples.

Rules:
- The root MUST always be a JSON array, even if it contains only one object.
- Output ONLY the JSON array.
- Do NOT use Markdown or code fences.
- Do NOT include any text before or after the JSON.
- Never render lists, numbering, or structured data inside a "text" string when
  a more specific object type exists for that data. Emit one object per item.
- Do NOT omit required fields.
- Preserve the order of the content as it should be presented to the user.
- Use one object for each distinct piece of content.
- Use "error" only when the request cannot be fulfilled.
- The JSON must always be valid and parseable.

Examples:

[
  {
    "type": "text",
    "text": "Hello!"
  }
]

[
  {
    "type": "text",
    "text": "Step 1: Open the application."
  },
  {
    "type": "text",
    "text": "Step 2: Select Settings."
  },
  {
    "type": "text",
    "text": "Step 3: Save your changes."
  }
]

[
  {
    "type": "error",
    "text": "I couldn't process your request."
  }
]
"""


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

    message = getattr(exc, "message", None) or getattr(exc, "error", None) or str(exc)
    # Keep it to the first line so we never dump a stack/JSON blob at the user.
    lines = [line for line in str(message).strip().splitlines() if line.strip()]
    if lines:
        return f"The AI provider returned an error: {lines[0]}"
    return "Something went wrong contacting the AI provider. Please try again."


def error_event(message: str) -> str:
    """NDJSON line the frontend renders as an error bubble. The content follows
    the same JSON-array contract the model uses, with a single `error` object,
    so ChatMessage displays it as an alert."""
    body = json.dumps([{"type": "error", "text": message}])
    return json.dumps({"content": body, "thinking": None, "done": True}) + "\n"


@router.post("/")
async def chat(body: ChatRequestTest,  user: Session = Depends(check_token)):
    provider = get_lmm_provider(body.provider)
    user_messages = body.messages
    model = body.model

    last_message = user_messages[-1].content

    mentioned_skill = find_skill(last_message)

    clean_message = (
        strip_trigger(last_message, mentioned_skill)
        if mentioned_skill
        else last_message
    )

    print(mentioned_skill, "mentioned ========")

    prompt = tool_calling_prompt.format(user_prompt=last_message)

    tool_history = []

    # The running "bill" for this request. Every model call adds to it.
    usage = TokenUsage()

    # Set if the tool phase fails; `generate` emits it instead of streaming so
    # the user sees a readable error rather than a broken/500 response.
    tool_error = None

    if mentioned_skill:
        try:
            async with mcp:
                tools = await MCPToolsCache.get_tools(mcp=mcp)

                messages = [
                    {"role": "system", "content": tool_phase_prompt},
                    {
                        "role": "system",
                        "content": f"tool instructions:\n{mentioned_skill.prompt()}",
                    },
                    {"role": "user", "content": clean_message},
                ]

                available_tools = [
                    tool
                    for tool in tools
                    if tool.name in mentioned_skill.tools
                ]

                # Generic OpenAI-style tool defs; each provider translates these
                # to its own wire format via `format_tools`, so this loop stays
                # provider-agnostic.
                generic_tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or "",
                            "parameters": sanitize_tool_schema(tool.inputSchema),
                        },
                    }
                    for tool in available_tools
                ]
                native_tools = provider.format_tools(generic_tools)

                MAX_TOOL_ITERATIONS = 25
                seen_calls = set()

                for _ in range(MAX_TOOL_ITERATIONS):
                    response = provider.chat(
                        model, messages, False, tools=native_tools,
                        options=SAMPLING_OPTIONS)

                    # Bill this call. Note the input token count climbs every
                    # iteration because `messages` keeps growing.
                    provider.add_usage(usage, response)
                    print(f"tool loop usage so far: {usage.to_dict()}")

                    tool_calls = provider.parse_tool_calls(response)

                    print(tool_calls, "tool calls ======")

                    if not tool_calls:
                        print("NO MORE TOOLS")
                        break

                    signature = tuple(
                        (tc["name"], json.dumps(tc["arguments"], sort_keys=True))
                        for tc in tool_calls
                    )

                    if signature in seen_calls:
                        raise RuntimeError("Tool loop detected.")

                    seen_calls.add(signature)

                    assistant_message = provider.build_assistant_message(response)
                    messages.append(assistant_message)
                    tool_history.append(assistant_message)

                    for tool_call in tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["arguments"]

                        if tool_name in USER_SCOPED_TOOLS:
                            tool_args = {**tool_args,
                                         "created_by": user["user_id"]}

                        result = await mcp.call_tool(tool_name, tool_args)

                        tool_response = result.structured_content

                        print(tool_response, "tool response ========")

                        tool_message = provider.build_tool_result_message(
                            tool_call, tool_response)

                        messages.append(tool_message)
                        tool_history.append(tool_message)
        except Exception as e:
            print(f"tool phase failed: {e!r}")
            tool_error = format_provider_error(e)

    def generate():
        # The tool phase already failed — surface it and don't attempt to stream.
        if tool_error:
            yield error_event(tool_error)
            return


        answer_messages = [{"role": "system", "content": test_prompt}]

        if mentioned_skill:
            answer_messages.append({
                "role": "system",
                "content": (
                    f"Skill output contract for '{mentioned_skill.name}'.\n"
                    "These instructions take precedence over the generic response\n"
                    "format above.\n\n"
                    "The contract below defines the SHAPE of your response ONLY.\n"
                    "Any object type shown is allowed, including its extra fields,\n"
                    "and you must match the structure exactly. But every VALUE\n"
                    "(text, labels, URLs, numbers) MUST come from the actual tool\n"
                    "results in this conversation. Any '...' or field-name text in\n"
                    "the contract is a placeholder — never emit it literally.\n\n"
                    f"{mentioned_skill.examples()}"
                ),
            })
            answer_messages.append({"role": "user", "content": clean_message})
            answer_messages.extend(tool_history)
            answer_messages.append({
                "role": "system",
                "content": (
                    "All tool calls are complete. Do not call any more tools.\n"
                    f'Answer the user\'s question: "{clean_message}"\n'
                    "Use ONLY the facts in the preceding 'tool' messages — build every\n"
                    "field of your answer (text, labels, URLs) from the values found\n"
                    "there. Do not use any topic, fact, or URL that is not in those\n"
                    "tool results.\n"
                    "Reply as a JSON array following the "
                    f"'{mentioned_skill.name}' output contract exactly.\n"
                    "Emit one object per item from the tool results — never collapse them\n"
                    "into a single text object.\n"
                    "Never restate the arguments you passed to a tool."
                ),
            })
        else:
            answer_messages.append({"role": "user", "content": prompt})

        try:
            stream = provider.chat(
                model, answer_messages, True, thinking=body.thinking,
                options=SAMPLING_OPTIONS)
            for chunk in provider.iter_stream(stream):

                print(chunk, "chunk ========")
                content = chunk["content"]
                thinking = chunk["thinking"]

                if content or thinking:
                    yield json.dumps({
                        "content": content,
                        "thinking": thinking,
                        "done": chunk["done"]
                    }) + "\n"

                if chunk["done"]:
                    if chunk["usage"]:
                        usage.add(chunk["usage"]["input"], chunk["usage"]["output"])
                    print(f"final request usage: {usage.to_dict()}")
                    # Emit the bill as a last event so the client can display it.
                    yield json.dumps({"usage": usage.to_dict(), "done": True}) + "\n"
                    break
        except Exception as e:
            # Errors here (rate limits, dead model, network) surface mid-stream;
            # emit a readable error event so the client shows it instead of the
            # response simply cutting off.
            print(f"answer stream failed: {e!r}")
            yield error_event(format_provider_error(e))

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )


class PingRequest(BaseModel):
    model: str
    provider: Optional[str] = None


@router.post("/ping")
def chat(body: PingRequest):
    model = body.model

    try:
        # Route through the provider factory so the check honors the requested
        # provider (ollama vs google), not just the Ollama-only repository path.
        return get_lmm_provider(body.provider).is_model_installed(model)
    except Exception as e:
        raise e


@router.get("/models")
def return_models(provider: Optional[str] = None):
    try:
        models = get_lmm_provider(provider).list_models()
        return models
    except Exception as e:
        raise e


class DummyChatRequest(BaseModel):
    prompt: str
    model: str


@router.post("/dummy")
def dummy_chat(body: DummyChatRequest):
    """Minimal non-streaming call to the active provider — handy for smoke-testing
    Gemini (or any provider) end to end without the tool/streaming machinery."""
    provider = get_lmm_provider()

    response = provider.chat(
        body.model,
        [{"role": "user", "content": body.prompt}],
        stream=False,
        options=SAMPLING_OPTIONS,
    )

    # Gemini returns a genai response object; Ollama returns a dict-like message.
    text = getattr(response, "text", None)
    if text is None:
        text = response.get("message", {}).get("content")

    return {"model": body.model, "response": text}
