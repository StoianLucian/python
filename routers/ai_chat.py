from typing import Optional

from fastapi import APIRouter, Depends
from db.connection import get_db
from db.schemas.chunk import Chunk
from lmm.factory import get_lmm_provider
from repositories.aiChat_repository import initialize_model_chat, is_model_installed, return_available_models, return_smallest_model
from prompts.prompts import rag_prompt, tool_calling_prompt, tool_phase_prompt, test_prompt, test_prompt2
from schemas import *
from fastapi.responses import StreamingResponse
import json
from fastmcp import Client

from repositories import *
from tools.cache.CMPToolsCache import MCPToolsCache
from tools.helpers import find_skill

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


mcp = Client("http://localhost:8000/mcp")


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


@router.post("/")
async def chat(body: ChatRequestTest,  db: Session = Depends(get_db)):
    provider = get_lmm_provider()
    user_messages = body.messages
    model = body.model

    last_message = user_messages[-1].content

    mentioned_skill = find_skill(last_message)

    prompt = tool_calling_prompt.format(user_prompt=last_message)

    tool_history = []

    if mentioned_skill:
        async with mcp:
            tools = await MCPToolsCache.get_tools(mcp=mcp)

            messages = [
                {"role": "system", "content": tool_phase_prompt},
                {
                    "role": "system",
                    "content": f"tool instructions:\n{mentioned_skill.prompt()}",
                },
                {"role": "user", "content": last_message},
            ]

            available_tools = [
                tool
                for tool in tools
                if tool.name in mentioned_skill.tools
            ]

            ollama_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema,
                    },
                }
                for tool in available_tools
            ]
            MAX_TOOL_ITERATIONS = 25
            seen_calls = set()

            for _ in range(MAX_TOOL_ITERATIONS):
                stream = provider.chat(
                    model, messages, False, tools=ollama_tools)
                tool_calls = stream.message.tool_calls

                print(tool_calls, "tool calls ======")

                if not tool_calls:
                    print("NO MORE TOOLS")
                    break
                signature = tuple(
                    (tc.function.name, json.dumps(
                        tc.function.arguments, sort_keys=True))
                    for tc in tool_calls
                )

                if signature in seen_calls:
                    raise RuntimeError("Tool loop detected.")

                seen_calls.add(signature)
                assistant_message = {
                    "role": "assistant",
                    "content": stream.message.content or "",
                }
                if stream.message.tool_calls:
                    assistant_message["tool_calls"] = [
                        tc.model_dump()
                        for tc in stream.message.tool_calls
                    ]

                messages.append(assistant_message)
                tool_history.append(assistant_message)

                for tool in tool_calls:
                    tool_name = tool.function.name
                    tool_args = tool.function.arguments

                    result = await mcp.call_tool(tool_name, tool_args)

                    tool_response = result.structured_content

                    print(tool_response, "tool response ========")

                    tool_message = {
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(tool_response),
                    }

                    messages.append(tool_message)
                    tool_history.append(tool_message)

    def generate():

        answer_messages = [{"role": "system", "content": test_prompt}]

        if mentioned_skill:
            answer_messages.append({
                "role": "system",
                "content": (
                    f"Skill output contract for '{mentioned_skill.name}'.\n"
                    "These instructions take precedence over the generic response\n"
                    "format above. Any object type used in the examples below is\n"
                    "allowed, including its extra fields, and must be reproduced\n"
                    "exactly as shown.\n\n"
                    f"{mentioned_skill.examples()}"
                ),
            })
            answer_messages.append({"role": "user", "content": last_message})
            answer_messages.extend(tool_history)
            answer_messages.append({
                "role": "system",
                "content": (
                    "All tool calls are complete. Do not call any more tools.\n"
                    "Report the outcome of the tool results to the user as a JSON array,\n"
                    f"following the '{mentioned_skill.name}' output contract exactly.\n"
                    "Emit one object per item from the tool results — never collapse them\n"
                    "into a single text object.\n"
                    "Never restate the arguments you passed to a tool."
                ),
            })
        else:
            answer_messages.append({"role": "user", "content": prompt})

        stream = provider.chat(model, answer_messages, True, thinking=False)
        for chunk in stream:

            content = chunk.get("message", {}).get("content")
            thinking = chunk.get("message", {}).get("thinking")
            isDone = chunk.get("done")

            if content or thinking:
                yield json.dumps({
                    "content": content,
                    "thinking": thinking,
                    "done": isDone
                }) + "\n"

            if chunk.get("done"):
                break

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )


class ChatRequest(BaseModel):
    model: str


@router.post("/ping")
def chat(body: ChatRequest):
    model = body.model

    try:
        return is_model_installed(model)
    except Exception as e:
        raise e


@router.get("/models")
def return_models():
    try:
        models = return_available_models()
        return models
    except Exception as e:
        raise e
