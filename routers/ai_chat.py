from typing import Optional

from fastapi import APIRouter, Depends
from db.connection import get_db
from db.schemas.chunk import Chunk
from helpers.helpers import return_context
from repositories.aiChat_repository import initialize_model_chat, is_model_installed, return_available_models
from prompts.prompts import rag_prompt
from schemas import *
from fastapi.responses import StreamingResponse
import json
from fastmcp import Client
from ollama import Client as OllamaClient
import os


from repositories import *

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


@router.post("/")
async def chat(body: ChatRequestTest,  db: Session = Depends(get_db)):
    messages = body.messages
    model = body.model

    last_message = messages[-1].content

    context = return_context(last_message, db)

    test_prompt = rag_prompt.format(
        context=context, user_question=last_message)

    messages = [
        {
            "role": "system",
            "content": "you are an AI assistant, your job is tu use the provided tools if appropriate to help the users do hes tasks"
        },
        *[
            {
                "role": m.role,
                "content": m.content
            }
            for m in body.messages
        ]
    ]
    
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
           
            stream = initialize_model_chat(model, messages, False, tools=ollama_tools)

            tools = stream.message.tool_calls

            print("TOOL IN PROGRESS", tools)

            # No more tool calls -> we're done
            if not tools:
                print("NO MORE TOOLS")
                break
            
            # messages.append({
            #     "role": "assistant",
            #     "content": stream.message.content,
            #     "tool_calls": [
            #         tc.model_dump()
            #         for tc in stream.message.tool_calls
            #     ],
            # })

            # Execute each requested tool
            for tool in tools:
                tool_name = tool.function.name
                tool_args = tool.function.arguments

                result = await mcp.call_tool(tool_name, tool_args)

                tool_response = result.structured_content

                messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps(tool_response),
                })
                
    print("MESSAGES after TOOLS" , messages[-1])

    def generate():
        stream = initialize_model_chat(model, messages, True)

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
