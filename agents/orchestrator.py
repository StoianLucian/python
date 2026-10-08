"""The Orchestrator: owns the control loop, tool execution, and streaming.

Flow (per the plan):
  resolve skill -> build scoped BlackBoard -> loop[ Planner -> Selector ->
  run tools -> Observer -> Evaluator ] -> (Clarifier | render_response | Answerer)

Each stage delegates to a SubAgent that receives only its scoped projection of
the blackboard. Progress is streamed as NDJSON thinking lines; the final answer
(or clarifying question) streams on the content channel. All sub-agent calls
bill one shared TokenUsage, emitted as the terminal event.
"""

import json
import time

from lmm.usage import TokenUsage
from tools.cache.mcp_tools_cache import MCPToolsCache
from tools.helpers import find_skill, strip_trigger, skill_for_tool
from routers.chat_helpers import (
    inject_scoped_args,
    sanitize_tool_schema,
    error_event,
    format_provider_error,
    thinking_step,
    timing_line,
    tool_step_label,
)

from agents.blackboard import BlackBoard, ToolCallRecord
from agents.base import ndjson
from agents.config import model_for
from agents.planner import PlannerAgent
from agents.selector import SelectorAgent
from agents.observer import ObserverAgent
from agents.evaluator import EvaluatorAgent
from agents.answerer import AnswererAgent, ClarifierAgent

# Each iteration is up to 4 model calls (Planner/Selector/Observer/Evaluator),
# so this cap is lower than v1's 6. A model that never says DONE still falls
# through to the Answerer with whatever was gathered.
MAX_ITERATIONS = 4
MAX_CALLS_PER_TOOL = 3


class Orchestrator:
    def __init__(self, provider, request_model, user, mcp, user_messages,
                 session_id=None):
        self.provider = provider
        self.request_model = request_model
        self.user = user
        self.mcp = mcp
        self.user_messages = user_messages
        self.session_id = session_id  # current conversation, for recall tool
        self.usage = TokenUsage()

        def make(cls, role):
            return cls(provider, model_for(role, request_model), self.usage)

        self.planner = make(PlannerAgent, "planner")
        self.selector = make(SelectorAgent, "selector")
        self.observer = make(ObserverAgent, "observer")
        self.evaluator = make(EvaluatorAgent, "evaluator")
        self.answerer = make(AnswererAgent, "answerer")
        self.clarifier = make(ClarifierAgent, "clarifier")

        self._step_no = 0

    def _label(self, text: str) -> str:
        self._step_no += 1
        return thinking_step(self._step_no, text)

    async def run(self):
        """Public entry: wraps the loop so any provider/tool error surfaces as a
        readable error event rather than a broken stream (like v1/v2)."""
        try:
            async for line in self._run():
                yield line
        except Exception as e:
            print(f"v3 orchestrator failed: {e!r}")
            yield error_event(format_provider_error(e))

    async def _run(self):
        provider = self.provider
        last_message = self.user_messages[-1].content

        # --- Skill resolution (same policy as v2) ---
        skill = find_skill(last_message)
        if skill:
            bb = BlackBoard(
                user_request=strip_trigger(last_message, skill),
                skill_name=skill.name,
                skill_prompt=skill.prompt(),
                output_contract=skill.examples(),
                allowed_tool_names=list(skill.tools),
            )
        else:
            bb = BlackBoard(user_request=last_message)

        # --- Available tools (restricted to the skill's, or all) ---
        tools = await MCPToolsCache.get_tools(mcp=self.mcp)
        if bb.allowed_tool_names:
            available = [t for t in tools if t.name in bb.allowed_tool_names]
        else:
            available = tools
            bb.allowed_tool_names = [t.name for t in tools]

        generic_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": sanitize_tool_schema(t.inputSchema),
                },
            }
            for t in available
        ]
        native_tools = provider.format_tools(generic_tools)

        # Loop guards (same approach as v2).
        seen_calls = set()
        tool_usage = {}
        # For the non-skill flow, collect the output contracts of tools the model
        # actually used, so the Answerer can match them. Skills already set the
        # contract up front.
        injected_contracts = {skill.name} if skill else set()

        for i in range(MAX_ITERATIONS):
            bb.iteration = i

            # 1. Planner
            yield self._label("Planning the next objective")
            t = time.perf_counter()
            out = {}
            async for line in self.planner.run(bb, out):
                yield line
            yield timing_line(time.perf_counter() - t)
            bb.plan.append(out["text"].strip())

            # 2. Selector (the only agent given tools)
            yield self._label("Selecting tools")
            t = time.perf_counter()
            out = {}
            async for line in self.selector.run(bb, out, native_tools=native_tools):
                yield line
            yield timing_line(time.perf_counter() - t)
            calls = out["tool_calls"]

            if calls:
                # Guard: a repeated identical call set, or hammering one tool,
                # means no new info — stop and answer with what we have.
                signature = tuple(
                    (c["name"], json.dumps(c["arguments"], sort_keys=True))
                    for c in calls
                )
                if signature in seen_calls or any(
                        tool_usage.get(c["name"], 0) >= MAX_CALLS_PER_TOOL
                        for c in calls):
                    print("v3: repeat/overused tool call — finishing")
                    bb.verdict = "DONE"
                    break
                seen_calls.add(signature)

                # 3. Run tools + 4. observe
                executed = []
                for call in calls:
                    name = call["name"]
                    args = call["arguments"]
                    yield self._label(tool_step_label(call))
                    tool_usage[name] = tool_usage.get(name, 0) + 1

                    # Inject server-controlled scoping (created_by / session_id).
                    args = inject_scoped_args(
                        name, args, self.user, self.session_id)

                    started = time.perf_counter()
                    result = await self.mcp.call_tool(name, args)
                    elapsed = time.perf_counter() - started
                    yield timing_line(elapsed, name)

                    bb.tool_calls.append(ToolCallRecord(
                        name, call["arguments"], result.structured_content,
                        elapsed, ok=True))
                    executed.append(bb.tool_calls[-1])

                    # Non-skill flow: pull in the owning skill's output contract.
                    if not skill:
                        owning = skill_for_tool(name)
                        if owning and owning.name not in injected_contracts:
                            example = owning.examples()
                            if example:
                                bb.output_contract += (
                                    ("\n\n" if bb.output_contract else "") + example)
                                injected_contracts.add(owning.name)

                yield self._label("Interpreting results")
                t = time.perf_counter()
                out = {}
                async for line in self.observer.run(bb, out, new_calls=executed):
                    yield line
                yield timing_line(time.perf_counter() - t)
                bb.observations.append(out["text"].strip())

            # 5. Evaluator
            yield self._label("Evaluating")
            t = time.perf_counter()
            out = {}
            async for line in self.evaluator.run(bb, out):
                yield line
            yield timing_line(time.perf_counter() - t)
            bb.verdict = out["text"].strip().upper()

            if "CLARIFY" in bb.verdict:
                break
            if "CONTINUE" in bb.verdict:
                continue
            break  # DONE / unrecognized -> go answer

        # --- Terminal stage ---
        if bb.verdict and "CLARIFY" in bb.verdict:
            yield self._label("Asking for clarification")
            async for line in self.clarifier.run(bb, {}):
                yield line
        else:
            shortcut = self._render_shortcut(bb, skill)
            if shortcut is not None:
                yield self._label("Composing the answer")
                yield ndjson(content=json.dumps(shortcut))
            else:
                yield self._label("Composing the answer")
                async for line in self.answerer.run(bb, {}):
                    yield line

        print(f"v3 chat usage: {self.usage.to_dict()}")
        yield json.dumps({"usage": self.usage.to_dict(), "done": True}) + "\n"

    def _render_shortcut(self, bb: BlackBoard, skill):
        """If the resolved skill can build the answer deterministically from the
        tool results (`render_response`), use that and skip the Answerer model
        call. Exercises the otherwise-dormant hook (e.g. web_search dedupe)."""
        if not skill or not bb.tool_calls:
            return None
        try:
            rendered = skill.render_response(bb.tool_history())
        except Exception as e:
            print(f"v3 render_response shortcut failed: {e!r}")
            return None
        return rendered
