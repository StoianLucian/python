from typing import Optional

from fastapi import APIRouter, Depends
from db.connection import get_db
from db.schemas.chunk import Chunk
from helpers.helpers import return_context
from repositories.aiChat_repository import initialize_model_chat, is_model_installed, return_available_models, return_smallest_model
from prompts.prompts import rag_prompt, tool_calling_prompt, test_prompt, test_prompt2
from schemas import *
from fastapi.responses import StreamingResponse
import json
from fastmcp import Client
from ollama import Client as OllamaClient
import os
from skills import AVAILABLE_SKILLS

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


modelUrl = os.getenv("MODEL_URL")

client = OllamaClient(
    host=modelUrl
)


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

The array may contain one or more objects. Each object MUST match EXACTLY one of the following schemas.

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

Rules:
- The root MUST always be a JSON array, even if it contains only one object.
- Output ONLY the JSON array.
- Do NOT use Markdown or code fences.
- Do NOT include any text before or after the JSON.
- Every element in the array must be one of the two allowed object types.
- Do NOT add extra fields.
- Do NOT omit required fields.
- Preserve the order of the content as it should be presented to the user.
- Use one object for each distinct piece of content.
- Use "text" for all normal responses.
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
    user_messages = body.messages
    model = body.model

    last_message = user_messages[-1].content
    
    mentioned_skill = find_skill(last_message)
    
    prompt = tool_calling_prompt.format(user_prompt=last_message)


    messages = [
        # {"role": "system", "content": test_prompt},
        {"role": "user", "content": last_message}
    ]
    
    if mentioned_skill:
        async with mcp:
            tools = await MCPToolsCache.get_tools(mcp=mcp)
            
            tool_instructions = {
                "role": "system",
                "content": f""" tool instructions:
            {mentioned_skill.prompt()}
            """
            }
            messages.append(tool_instructions)
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
                stream = initialize_model_chat(model, messages, False, tools=ollama_tools)
                tool_calls = stream.message.tool_calls
                
                print(tool_calls, "tool calls ======")

                if not tool_calls:
                    print("NO MORE TOOLS")
                    break
                signature = tuple(
                    (tc.function.name, json.dumps(tc.function.arguments, sort_keys=True))
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

                for tool in tool_calls:
                    tool_name = tool.function.name
                    tool_args = tool.function.arguments

                    result = await mcp.call_tool(tool_name, tool_args)

                    tool_response = result.structured_content

                    messages.append({
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(tool_response),
                    })

    def generate():
        # smallest_model = return_smallest_model()
        format = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["text", "popover", "error"]
                    },
                    "text": {
                        "type": "string"
                    },
                    "source_id": {
                        "type": "number"
                    },
                    "page_number": {
                        "type": "number"
                    }
                },
                "required": ["type", "text"],
                "additionalProperties": False
            }
        }
        
        if mentioned_skill:
            messages.append({"role": "system", "content": f"return format examples : {mentioned_skill.examples()}"})
            
        stream = initialize_model_chat(model, messages, True, thinking=False)

        for chunk in stream:

            content = chunk.get("message", {}).get("content")
            thinking = chunk.get("message", {}).get("thinking")
            isDone = chunk.get("done")
            
            print(chunk, "chunk ================")

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
