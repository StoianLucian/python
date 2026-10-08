from typing import Optional

from fastapi import APIRouter, Depends
from lmm.factory import get_lmm_provider
from lmm.usage import TokenUsage
from repositories.ai_chat_repository import is_model_installed, return_available_models
from prompts.prompts import agent_prompt, router_prompt
from schemas import *
from fastapi.responses import StreamingResponse
import json
import os
import time
from fastmcp import Client
from import_folder.mcp_server import mcp as mcp_server

from repositories import *
from tools.cache.mcp_tools_cache import MCPToolsCache
from tools.helpers import find_skill, strip_trigger, skill_for_tool

# Shared, dependency-light helpers and request models (extracted so the `agents/`
# multi-agent path can reuse them without importing this module).
from routers.chat_helpers import (
    ChatRequestTest,
    USER_SCOPED_TOOLS,
    SAMPLING_OPTIONS,
    sanitize_tool_schema,
    format_provider_error,
    to_provider_messages,
    error_event,
    thinking_step,
    timing_line,
    tool_step_label,
)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


class ChatRequest(BaseModel):
    prompt: str
    model: str


# Connect to the in-process FastMCP server directly (in-memory transport).
# Passing the server instance avoids an HTTP round-trip to ourselves, so it
# works regardless of the port uvicorn binds to (e.g. Render's $PORT) and needs
# no separate MCP server process.
mcp = Client(mcp_server)


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


def route_needs_tools(provider, model, tools, message, usage) -> bool:
    """Fast pre-flight classification: does this message need any tool?

    A separate, cheap model call (``ROUTER_MODEL`` env, or the request model)
    that answers YES/NO, so the "understand + decide on tools" decision is a
    discrete, timeable step. Reuses `stream_turn` to read the text and bill the
    call. Defaults to allowing tools unless the model clearly says NO, so a
    router hiccup never silently strips tools the request needs."""
    router_model = os.getenv("ROUTER_MODEL") or model
    tool_list = "\n".join(f"- {t.name}: {t.description or ''}" for t in tools)
    router_messages = [
        {"role": "system", "content": router_prompt},
        {
            "role": "user",
            "content": (
                f"Available tools:\n{tool_list}\n\n"
                f"User message:\n{message}\n\n"
                "Answer YES or NO:"
            ),
        },
    ]

    text = ""
    stream = provider.chat(
        router_model, router_messages, True, options=SAMPLING_OPTIONS)
    for ev in provider.stream_turn(stream):
        if ev["content"]:
            text += ev["content"]
        if ev["done"] and ev["usage"]:
            usage.add(ev["usage"]["input"], ev["usage"]["output"])

    print(f"router decision: {text!r}")
    return not text.strip().lower().startswith("no")


@router.post("/")
async def chat(body: ChatRequestTest, user: Session = Depends(check_token)):
    """Default chat endpoint (current implementation, same as v2)."""
    return await _run_chat_v2(body, user)


@router.post("/v1")
async def chat_v1(body: ChatRequestTest, user: Session = Depends(check_token)):
    """v1: a single agentic chat loop that streams content live (no router,
    no separate JSON answer turn)."""
    return await _run_chat_v1(body, user)


@router.post("/v2")
async def chat_v2(body: ChatRequestTest, user: Session = Depends(check_token)):
    """v2: router + streaming gather loop + dedicated JSON answer turn."""
    return await _run_chat_v2(body, user)


@router.post("/v3")
async def chat_v3(body: ChatRequestTest, user: Session = Depends(check_token)):
    """v3 (experimental): orchestrator + specialized sub-agents, each with its
    own scoped context (see the `agents/` package)."""
    return await _run_chat_v3(body, user)


async def _run_chat_v3(body: ChatRequestTest, user):
    """Thin entry for the multi-agent path: build the provider, open the MCP
    client once, and stream the Orchestrator's events. All the control flow lives
    in `agents.orchestrator.Orchestrator`. Imported lazily to keep this module's
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


async def _run_chat_v2(body: ChatRequestTest, user):
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

    async def generate():
        # The running "bill" for this request. Every model call adds to it.
        usage = TokenUsage()

        # Monotonic counter for the numbered progress steps we stream on the
        # `thinking` channel in place of the model's raw reasoning.
        step_no = 0

        def next_step(label: str) -> str:
            nonlocal step_no
            step_no += 1
            return thinking_step(step_no, label)

        # ---- Single agentic loop: the model understands the request, decides
        # whether tools are needed, calls them (looping until done), then streams
        # its final answer directly — no separate synthesis pass. Numbered steps
        # go on the `thinking` channel; answer text is forwarded live as it
        # arrives. When a skill is mentioned we restrict the model to that skill's
        # tools and prime it with the skill instructions and output contract;
        # otherwise we expose every tool and let the model decide. On failure,
        # surface a readable error rather than a broken stream. ----
        try:
            async with mcp:
                tools = await MCPToolsCache.get_tools(mcp=mcp)

                if mentioned_skill:
                    # Restrict to the skill's tools and prime with its prompt and
                    # output contract.
                    available_tools = [
                        tool
                        for tool in tools
                        if tool.name in mentioned_skill.tools
                    ]
                    messages = [
                        {"role": "system", "content": agent_prompt},
                        {
                            "role": "system",
                            "content": f"tool instructions:\n{mentioned_skill.prompt()}",
                        },
                        {
                            "role": "system",
                            "content": (
                                f"Output contract for '{mentioned_skill.name}'. This defines the\n"
                                "SHAPE of your final JSON answer — match the structure exactly, but\n"
                                "every VALUE (text, labels, URLs, numbers) MUST come from the actual\n"
                                "tool results in this conversation. Never emit placeholder or '...'\n"
                                "text, and never restate the arguments you passed to a tool.\n\n"
                                f"{mentioned_skill.examples()}"
                            ),
                        },
                        {"role": "user", "content": clean_message},
                    ]
                else:
                    # No skill mentioned: pass the full conversation so the model
                    # has the context to answer, and let the router below decide
                    # whether tools should be exposed at all.
                    available_tools = tools
                    messages = [
                        {"role": "system", "content": agent_prompt},
                        *to_provider_messages(user_messages),
                    ]

                # Decide whether tools are needed. A skill mention is an explicit
                # request for that skill's tools, so we skip routing. Otherwise a
                # fast, separate classifier makes — and lets us time — the
                # "understand the request + decide on tools" step on its own.
                if mentioned_skill:
                    needs_tools = True
                else:
                    yield next_step("Understanding your request & deciding on tools")
                    router_started = time.perf_counter()
                    needs_tools = route_needs_tools(
                        provider, model, tools, clean_message, usage)
                    yield timing_line(time.perf_counter() - router_started)

                # Generic OpenAI-style tool defs; each provider translates these
                # to its own wire format via `format_tools`, so the loop stays
                # provider-agnostic. When no tools are needed we expose none, so
                # the model answers directly.
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
                ] if needs_tools else []
                native_tools = (
                    provider.format_tools(generic_tools) if needs_tools else None
                )

                MAX_TOOL_ITERATIONS = 8
                MAX_CALLS_PER_TOOL = 3
                seen_calls = set()
                tool_usage = {}
                # Response-format contracts already injected, so we add each
                # tool's format at most once.
                injected_formats = set()

                # --- Tool-gathering loop: only runs when tools are exposed. These
                # turns produce tool calls, not the final answer, so we do NOT
                # forward their content — the answer is composed separately below
                # in a JSON-enforced, tool-free turn (format="json" can't be mixed
                # with tools on all providers). ---
                if needs_tools:
                    for i in range(MAX_TOOL_ITERATIONS):
                        yield next_step(
                            "Selecting the right tools" if i == 0
                            else "Deciding what to do next"
                        )
                        turn_started = time.perf_counter()

                        stream = provider.chat(
                            model, messages, True, tools=native_tools,
                            options=SAMPLING_OPTIONS, thinking=body.thinking)

                        tool_calls = []
                        assistant_message = None

                        for ev in provider.stream_turn(stream):
                            if ev["done"]:
                                tool_calls = ev["tool_calls"] or []
                                assistant_message = ev["assistant_message"]
                                if ev["usage"]:
                                    usage.add(ev["usage"]["input"],
                                              ev["usage"]["output"])

                        yield timing_line(time.perf_counter() - turn_started)

                        print(tool_calls, "tool calls ======")

                        if not tool_calls:
                            # Model is done gathering; go compose the answer.
                            break

                        # Loop guards: stop gathering (and answer with what we
                        # already have) if the model repeats an identical call, or
                        # keeps hammering the same tool — small models often
                        # re-search with a reworded query instead of answering.
                        signature = tuple(
                            (tc["name"], json.dumps(tc["arguments"], sort_keys=True))
                            for tc in tool_calls
                        )
                        if signature in seen_calls:
                            print("repeat tool call — composing answer")
                            break
                        if any(tool_usage.get(tc["name"], 0) >= MAX_CALLS_PER_TOOL
                               for tc in tool_calls):
                            print("per-tool call cap reached — composing answer")
                            break
                        seen_calls.add(signature)

                        # Preserve the model's tool-call turn in history.
                        messages.append(assistant_message)

                        for tool_call in tool_calls:
                            # Numbered progress step for this call, sent before we
                            # block on it so the user sees each (possibly refined) step.
                            yield next_step(tool_step_label(tool_call))

                            tool_name = tool_call["name"]
                            tool_args = tool_call["arguments"]
                            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

                            if tool_name in USER_SCOPED_TOOLS:
                                tool_args = {**tool_args,
                                             "created_by": user["user_id"]}

                            started = time.perf_counter()
                            result = await mcp.call_tool(tool_name, tool_args)
                            elapsed = time.perf_counter() - started

                            # Surface how long the call took, right under its step.
                            yield timing_line(elapsed, tool_name)

                            tool_response = result.structured_content

                            print(tool_response, "tool response ========")

                            messages.append(provider.build_tool_result_message(
                                tool_call, tool_response))

                        # Inject the response-format contract for each tool the
                        # model used, so it shapes the final answer correctly. The
                        # skill path already primes its contract up front; here we
                        # cover tools the model chose on its own (non-skill flow).
                        if not mentioned_skill:
                            for tool_call in tool_calls:
                                owning = skill_for_tool(tool_call["name"])
                                if not owning or owning.name in injected_formats:
                                    continue
                                examples = owning.examples()
                                if not examples:
                                    continue
                                messages.append({
                                    "role": "system",
                                    "content": (
                                        f"You used the '{owning.name}' tool, so its "
                                        "response-format contract below is MANDATORY. "
                                        "Use the EXACT object types it defines — this "
                                        "includes the citation objects (e.g. a "
                                        "\"popover\" with \"text\", verbatim "
                                        "\"content\", \"source_id\", and "
                                        "\"page_number\", or a \"url\"). You MUST emit "
                                        "one such citation object for each tool result "
                                        "you rely on; do NOT reply with a plain text "
                                        "object alone. Build every value from the "
                                        "actual tool results above — never invent or "
                                        f"emit placeholder or '...' values.\n\n{examples}"
                                    ),
                                })
                                injected_formats.add(owning.name)

                    # Nudge the transition from gathering to answering.
                    messages.append({
                        "role": "system",
                        "content": (
                            "All needed information has been gathered. Do not call "
                            "any tools now. Write the final answer to the user as a "
                            "single valid JSON array, following the response format "
                            "and any tool contracts above, using only facts from the "
                            "tool results. Include the citation objects those "
                            "contracts require (e.g. a \"popover\" for each document "
                            "result used) — do not answer with plain text alone."
                        ),
                    })

                # --- Answer turn: no tools, JSON enforced, streamed live. A
                # dedicated tool-free turn lets us force valid JSON output
                # (format="json"), which providers can't combine with tools. ---
                yield next_step("Building the answer")
                answer_started = time.perf_counter()

                answer_stream = provider.chat(
                    model, messages, True, options=SAMPLING_OPTIONS,
                    thinking=False, format="json")

                for ev in provider.stream_turn(answer_stream):
                    if ev["content"]:
                        yield json.dumps({
                            "content": ev["content"],
                            "thinking": None,
                            "done": False,
                        }) + "\n"
                    if ev["done"] and ev["usage"]:
                        usage.add(ev["usage"]["input"], ev["usage"]["output"])

                yield timing_line(time.perf_counter() - answer_started)

                print(f"final request usage: {usage.to_dict()}")
                # Emit the bill as a last event so the client can display it.
                yield json.dumps({"usage": usage.to_dict(), "done": True}) + "\n"
        except Exception as e:
            print(f"agent loop failed: {e!r}")
            yield error_event(format_provider_error(e))
            return

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )


# Instruction text for each stage of the v1 agent loop. The flow is:
#   understand →
#     { plan & select tools → run tools → read tool results → evaluate }* →
#   formulate response
# Evaluate decides whether to loop again (more tool calls), stop and ask the user
# a clarifying question, or finish and formulate the answer. Each instruction is
# injected as a system message right before that stage's model turn. Edit these
# to change how the agent reasons.
UNDERSTAND_INSTRUCTION = (
    "Understand the question. Briefly restate, in one or two sentences, what the "
    "user is asking and what a complete answer needs. Do not answer yet."
)
PLAN_SELECT_INSTRUCTION = (
    "Plan your next move and act on it. In one or two sentences, say what needs to "
    "happen next to get closer to answering, then — if a tool is needed now — call "
    "it (you may call more than one). If no tool is needed, don't call any. Do not "
    "write the final answer."
)
READ_RESULTS_INSTRUCTION = (
    "Read the tool results above. In one or two sentences, summarize what they "
    "tell you that is relevant to the user's question. Do not call tools and do "
    "not write the final answer yet."
)
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
    "response format and any tool output-format examples shown above exactly — "
    "match their object SHAPE, but build every value from this conversation and "
    "the tool results above. Do not mention these steps and do not call any tools."
)

# Hard cap on loop iterations, so a model that never says DONE can't loop forever.
MAX_LOOP_ITERATIONS = 6


async def _run_chat_v1(body: ChatRequestTest, user):
    """v1: a ReAct-style agent loop. The model is driven through explicit stages —
    understand the question, then repeatedly plan, select tools, execute them,
    observe the results and evaluate — until it decides it's DONE (go write the
    answer) or needs to CLARIFY (ask the user a question and end the turn). Tools
    are executed for real and their results fed back as observations. Each stage's
    label, elapsed time and token usage are streamed on the thinking channel;
    only the final answer (or clarifying question) is streamed as content."""
    provider = get_lmm_provider(body.provider)
    user_messages = body.messages
    model = body.model

    async def generate():
        usage = TokenUsage()

        messages = [
            {"role": "system", "content": agent_prompt},
            *to_provider_messages(user_messages),
        ]

        # Monotonic step counter for the numbered progress labels.
        step_no = 0

        def next_label(label: str) -> str:
            nonlocal step_no
            step_no += 1
            return thinking_step(step_no, label)

        def token_line(step_usage: TokenUsage) -> str:
            return json.dumps({
                "thinking": (
                    f"   ↳ {step_usage.total_tokens} tokens "
                    f"({step_usage.input_tokens} in / "
                    f"{step_usage.output_tokens} out)\n"
                ),
                "done": False,
            }) + "\n"

        async def do_turn(instruction, label, out, *,
                          tools=None, as_answer=False, fmt=None):
            """Run one model turn for a stage: show the label, inject the stage
            instruction, stream the turn (answer stages → content channel, others
            → thinking), report time + tokens, and keep the turn in history. The
            turn's accumulated text, tool calls and assistant message are written
            into `out` for the caller."""
            yield next_label(label)
            messages.append({"role": "system", "content": instruction})

            step_started = time.perf_counter()
            step_usage = TokenUsage()

            stream = provider.chat(
                model, messages, True, tools=tools,
                options=SAMPLING_OPTIONS, thinking=body.thinking, format=fmt)

            text = ""
            tool_calls = []
            assistant_message = None
            for response in provider.stream_turn(stream):
                if response["content"] or response["thinking"]:
                    if as_answer:
                        payload = {"content": response["content"],
                                   "thinking": response["thinking"]}
                    else:
                        merged = (response["thinking"] or "") + \
                            (response["content"] or "")
                        payload = {"content": None, "thinking": merged or None}
                    yield json.dumps({**payload, "done": False}) + "\n"
                if response["content"]:
                    text += response["content"]
                if response["done"]:
                    tool_calls = response["tool_calls"] or []
                    assistant_message = response["assistant_message"]
                    if response["usage"]:
                        usage.add(response["usage"]["input"],
                                  response["usage"]["output"])
                        step_usage.add(response["usage"]["input"],
                                       response["usage"]["output"])

            if assistant_message is not None:
                messages.append(assistant_message)

            yield timing_line(time.perf_counter() - step_started)
            yield token_line(step_usage)

            out["text"] = text
            out["tool_calls"] = tool_calls

        try:
            async with mcp:
                tools = await MCPToolsCache.get_tools(mcp=mcp)

                # Generic OpenAI-style tool defs; each provider translates these
                # to its own wire format via `format_tools`.
                generic_tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or "",
                            "parameters": sanitize_tool_schema(tool.inputSchema),
                        },
                    }
                    for tool in tools
                ]
                native_tools = provider.format_tools(generic_tools)

                # Tools actually executed, so the answer step can inject their
                # output-format examples.
                executed_tools = []
                answered = False

                # 1. Understand (once).
                out = {}
                async for line in do_turn(
                        UNDERSTAND_INSTRUCTION, "Understanding your question", out):
                    yield line

                # Loop: plan & select tools → run tools → read results →
                # evaluate, repeating while more tool calls are needed.
                for _ in range(MAX_LOOP_ITERATIONS):
                    # Plan & select tools (the model plans, then calls any tools).
                    out = {}
                    async for line in do_turn(
                            PLAN_SELECT_INSTRUCTION, "Planning & selecting tools",
                            out, tools=native_tools):
                        yield line
                    tool_calls = out["tool_calls"]

                    # Run tools: execute each call and feed the result back into
                    # the conversation as an observation.
                    for tool_call in tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["arguments"]
                        yield next_label(
                            f"Running {tool_name}("
                            f"{json.dumps(tool_args)})")

                        if tool_name in USER_SCOPED_TOOLS:
                            tool_args = {**tool_args,
                                         "created_by": user["user_id"]}

                        started = time.perf_counter()
                        result = await mcp.call_tool(tool_name, tool_args)
                        yield timing_line(
                            time.perf_counter() - started, tool_name)

                        executed_tools.append(tool_name)
                        messages.append(provider.build_tool_result_message(
                            tool_call, result.structured_content))

                    # Read tool results: have the model interpret the observations
                    # (only when there were any).
                    if tool_calls:
                        out = {}
                        async for line in do_turn(
                                READ_RESULTS_INSTRUCTION, "Reading tool results",
                                out):
                            yield line

                    # Evaluate: decide whether to loop, clarify, or finish.
                    out = {}
                    async for line in do_turn(
                            EVALUATE_INSTRUCTION, "Evaluating", out):
                        yield line
                    verdict = out["text"].strip().upper()

                    if "CLARIFY" in verdict:
                        # Ask the user a question and end the turn.
                        out = {}
                        async for line in do_turn(
                                CLARIFY_INSTRUCTION, "Asking for clarification",
                                out, as_answer=True, fmt="json"):
                            yield line
                        answered = True
                        break
                    if "CONTINUE" in verdict:
                        continue  # more work — loop back to plan & select
                    break  # DONE (or unrecognized) — go formulate the answer

                # Formulate the answer (unless we already asked for clarification).
                if not answered:
                    # Inject the output-format example for each executed tool's
                    # skill so the model shapes its JSON answer to match (deduped).
                    injected = set()
                    for tool_name in executed_tools:
                        owning = skill_for_tool(tool_name)
                        if not owning or owning.name in injected:
                            continue
                        example = owning.examples()
                        if not example:
                            continue
                        messages.append({
                            "role": "system",
                            "content": (
                                f"Output-format example for the '{owning.name}' "
                                f"tool — match this shape exactly:\n\n{example}"
                            ),
                        })
                        injected.add(owning.name)

                    out = {}
                    async for line in do_turn(
                            ANSWER_INSTRUCTION, "Formulating the answer", out,
                            as_answer=True, fmt="json"):
                        yield line

                # Grand total token count across all steps, on the thinking
                # channel. (Elapsed time is rendered by the frontend.)
                yield json.dumps({
                    "thinking": (
                        f"Total: {usage.total_tokens} tokens "
                        f"({usage.input_tokens} in / {usage.output_tokens} out)\n"
                    ),
                    "done": False,
                }) + "\n"

            print(f"v1 chat usage: {usage.to_dict()}")
            yield json.dumps({"usage": usage.to_dict(), "done": True}) + "\n"
        except Exception as e:
            print(f"v1 chat failed: {e!r}")
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
