
import json
from typing import Optional

# from fastmcp import FastMCP
from fastapi import APIRouter, Depends
from db.connection import get_db
from schemas import *
import os

from fastmcp import Client
from ollama import Client as OllamaClient


from db.schemas.user import User


from repositories import *

router = APIRouter(
    prefix="/bot",
    tags=["bot"],
)

class Message(BaseModel):
    role: str
    content: str
    images: Optional[list[str]] = None

class BotRequest(BaseModel):
    messages: list[Message]
    model: str


modelUrl = os.getenv("MODEL_URL")

client = OllamaClient(
    host=modelUrl
)

prompt ="""

    You are a helpful AI assistant with access to external tools.

    When answering a user's request:

    If a tool can provide the information more accurately or perform the requested action, use the appropriate tool.
    Do not invent or guess information that a tool can retrieve.
    Select the most appropriate tool based on its name and description.
    Provide all required arguments when calling a tool.
    If required information is missing, ask the user for clarification before calling a tool.
    After receiving the tool result, use that result to produce the final answer.
    Do not mention internal tool names or describe the tool-calling process unless the user asks.
    If a tool returns an error, explain the issue to the user and, when appropriate, suggest how they can resolve it.
    If multiple tools are needed, call them in the logical order and combine their results into a single response.
    Never fabricate tool results.

    When a tool returns an object containing:

    success: indicates whether the operation succeeded.
    result: contains the data returned by the tool.

    If success is true, use the contents of result to answer the user naturally.

    If success is false, explain the error contained in result and do not pretend the operation succeeded.

"""

mcp = Client("http://localhost:8000/mcp")

@router.post("/")
async def chat(body: BotRequest):
    messages = [
        {
            "role": "system",
            "content": prompt,
        },
        *body.messages,
    ]

    model = body.model

    async with mcp:
        tools = await mcp.list_tools()


        ollama_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools
        ]

        while True:
            response = client.chat(
                model=model,
                messages=messages,
                tools=ollama_tools,
            )

            message = response.message

            # Save the assistant message (may contain tool calls)
            messages.append(message)

            # No more tool calls -> we're done
            if not message.tool_calls:
                return message.content

            # Execute each requested tool
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments

                result = await mcp.call_tool(tool_name, tool_args)

                tool_response = result.structured_content

                messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps(tool_response),
                })

    
   