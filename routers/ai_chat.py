from typing import Optional

from fastapi import APIRouter, Depends
from lmm.factory import get_lmm_provider
from schemas import *
from fastapi.responses import StreamingResponse
from fastmcp import Client
from import_folder.mcp_server import mcp as mcp_server

from repositories import *

# Shared request model (extracted so the `agents/` multi-agent path can reuse it
# without importing this module).
from routers.chat_helpers import ChatRequestTest

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


# Connect to the in-process FastMCP server directly (in-memory transport).
# Passing the server instance avoids an HTTP round-trip to ourselves, so it
# works regardless of the port uvicorn binds to (e.g. Render's $PORT) and needs
# no separate MCP server process.
mcp = Client(mcp_server)


@router.post("/")
async def chat(body: ChatRequestTest, user: Session = Depends(check_token)):
    """Chat endpoint: builds the provider, opens the in-process MCP client once,
    and streams the Orchestrator's events (the single tool-calling loop lives in
    `agents.orchestrator.Orchestrator`). Imported lazily to keep this module's
    import graph independent of `agents/`."""
    from agents.orchestrator import Orchestrator

    provider = get_lmm_provider(body.provider)

    async def generate():
        async with mcp:
            orchestrator = Orchestrator(
                provider=provider,
                request_model=body.model,
                user=user,
                mcp=mcp,
                user_messages=body.messages,
                session_id=body.session_id,
            )
            async for line in orchestrator.run():
                yield line

    return StreamingResponse(generate(), media_type="application/x-ndjson")


class PingRequest(BaseModel):
    model: str
    provider: Optional[str] = None


@router.post("/ping")
def ping(body: PingRequest):
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
