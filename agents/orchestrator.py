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

from agents.blackboard import BlackBoard
from agents.base import ndjson
from routers.chat_helpers import SAMPLING_OPTIONS
from prompts.prompts import agent_prompt

# One model drives the whole turn: it calls tools, sees their results in the same
# context, and keeps going until it answers. Each iteration is a single model
# call (+ any tools it requested), so the cap can be generous.
MAX_ITERATIONS = 6
MAX_CALLS_PER_TOOL = 3


def _is_explicit_only(tool_name: str) -> bool:
    """True if the tool belongs to an `explicit_only` skill — excluded from the
    default toolset and only offered when the user invokes that skill directly."""
    owning = skill_for_tool(tool_name)
    return bool(owning and getattr(owning, "explicit_only", False))


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

        # Prior-conversation context: the session's rolling summary + the few
        # newest messages, fetched server-side so the client doesn't resend the
        # whole history each turn. Empty for a brand-new session.
        history = self._conversation_history()

        # --- Skill resolution (same policy as v2) ---
        skill = find_skill(last_message)
        if skill:
            bb = BlackBoard(
                user_request=strip_trigger(last_message, skill),
                history=history,
                skill_name=skill.name,
                skill_prompt=skill.prompt(),
                output_contract=skill.examples(),
                allowed_tool_names=list(skill.tools),
            )
        else:
            bb = BlackBoard(user_request=last_message, history=history)

        # --- Available tools (restricted to the skill's, or all) ---
        tools = await MCPToolsCache.get_tools(mcp=self.mcp)
        if bb.allowed_tool_names:
            available = [t for t in tools if t.name in bb.allowed_tool_names]
        else:
            # Default toolset excludes "explicit_only" tools (e.g. execute_sql):
            # too powerful/general to offer on every request — the model would
            # over-reach for them. They're only available via their trigger.
            available = [t for t in tools if not _is_explicit_only(t.name)]
            bb.allowed_tool_names = [t.name for t in available]

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

        # --- Single tool-calling loop ---------------------------------------
        # One model, one growing conversation: it calls tools, sees their results
        # in the SAME context, and keeps going until it stops calling tools (that
        # final turn is the answer). This is what makes multi-step flows like
        # `lookup_* -> add_*` reliable — the lookup result stays in view when the
        # model decides the next call.
        messages = [
            {"role": "system", "content": self._build_system_prompt(bb)},
            {
                "role": "user",
                "content": bb.user_request,
                "images": getattr(self.user_messages[-1], "images", None),
            },
        ]

        # Output contracts already in the system prompt for a skill; for the
        # non-skill flow we append each used tool's contract the first time.
        injected_contracts = {skill.name} if skill else set()
        seen_calls = set()
        tool_usage = {}
        answered = False
        # Document chunks returned by search_documents this turn — used to
        # guarantee the answer carries source markers (popover triggers) even if
        # the model forgets to cite them.
        doc_sources: list[dict] = []

        for iteration in range(MAX_ITERATIONS):
            turn_text = ""
            tool_calls = []
            assistant_message = None

            print(f"[loop] iteration {iteration + 1}/{MAX_ITERATIONS} — model turn")
            stream = provider.chat(
                self.request_model, messages, True,
                tools=native_tools, options=SAMPLING_OPTIONS, thinking=False,
            )
            for ev in provider.stream_turn(stream):
                if ev["thinking"]:
                    yield ndjson(thinking=ev["thinking"])
                if ev["content"]:
                    turn_text += ev["content"]
                if ev["done"]:
                    tool_calls = ev["tool_calls"] or []
                    assistant_message = ev["assistant_message"]
                    if ev["usage"]:
                        self.usage.add(ev["usage"]["input"], ev["usage"]["output"])

            # No tool calls -> this turn is the final answer.
            if not tool_calls:
                turn_text = self._ensure_doc_sources(turn_text, doc_sources)
                print(f"[answer] model={self.request_model} has_marker={'[[source:' in turn_text}\n{turn_text}")
                yield self._label("Composing the answer")
                yield ndjson(content=turn_text)
                answered = True
                break

            print(f"[loop] model requested {len(tool_calls)} tool call(s): "
                  f"{', '.join(c['name'] for c in tool_calls)}")

            # Loop guard: an identical call set or hammering one tool means no new
            # progress — stop tool use and force a final answer below.
            signature = tuple(
                (c["name"], json.dumps(c["arguments"], sort_keys=True))
                for c in tool_calls
            )
            if signature in seen_calls or any(
                    tool_usage.get(c["name"], 0) >= MAX_CALLS_PER_TOOL
                    for c in tool_calls):
                print("v3: repeat/overused tool call — finishing")
                break
            seen_calls.add(signature)

            # Keep the model's tool-call turn, run each tool, feed results back.
            messages.append(assistant_message)
            for call in tool_calls:
                name = call["name"]
                yield self._label(tool_step_label(call))
                tool_usage[name] = tool_usage.get(name, 0) + 1

                args = inject_scoped_args(
                    name, call["arguments"], self.user, self.session_id)

                print(f"[tool] ▶ START {name} args={json.dumps(call['arguments'], default=str)}")
                started = time.perf_counter()
                try:
                    result = await self.mcp.call_tool(name, args)
                except Exception as e:
                    print(f"[tool] ✖ ERROR {name} after {time.perf_counter() - started:.2f}s: {e!r}")
                    raise
                elapsed = time.perf_counter() - started
                result_preview = json.dumps(result.structured_content, default=str)
                if len(result_preview) > 500:
                    result_preview = result_preview[:500] + "...(truncated)"
                print(f"[tool] ✔ END   {name} in {elapsed:.2f}s -> {result_preview}")
                yield timing_line(elapsed, name)

                messages.append(
                    provider.build_tool_result_message(
                        call, result.structured_content))

                if name == "search_documents":
                    doc_sources.extend(
                        self._extract_doc_sources(result.structured_content))

                # Non-skill flow: append the owning skill's output contract once,
                # so the final answer uses the right objects (popovers, etc.).
                if not skill:
                    owning = skill_for_tool(name)
                    if owning and owning.name not in injected_contracts:
                        example = owning.examples()
                        if example:
                            messages.append({
                                "role": "system",
                                "content": "Output-format contract (match the object SHAPE EXACTLY):\n" + example,
                            })
                            injected_contracts.add(owning.name)

        # Hit the iteration cap (or tripped the loop guard) still wanting tools:
        # make one final call with tools disabled so the model must answer.
        if not answered:
            yield self._label("Composing the answer")
            stream = provider.chat(
                self.request_model, messages, True,
                tools=None, options=SAMPLING_OPTIONS, thinking=False,
            )
            final = ""
            for ev in provider.stream_turn(stream):
                if ev["content"]:
                    final += ev["content"]
                if ev["done"] and ev["usage"]:
                    self.usage.add(ev["usage"]["input"], ev["usage"]["output"])
            yield ndjson(content=self._ensure_doc_sources(final, doc_sources))

        print(f"v3 chat usage: {self.usage.to_dict()}")
        yield json.dumps({"usage": self.usage.to_dict(), "done": True}) + "\n"

    @staticmethod
    def _extract_doc_sources(result) -> list[dict]:
        """Pull {source_id, page_number, content} rows out of a search_documents
        result (tolerating the ToolResponse `{"result": [...]}` wrapper)."""
        payload = result.get("result", result) if isinstance(result, dict) else result
        if not isinstance(payload, list):
            return []
        return [
            {
                "source_id": item.get("source_id"),
                "page_number": item.get("page_number") or 1,
                "content": item.get("content") or "",
            }
            for item in payload
            if isinstance(item, dict) and item.get("source_id") is not None
        ]

    @staticmethod
    def _ensure_doc_sources(text: str, doc_sources: list[dict]) -> str:
        """Guarantee the answer can trigger the source popover: if documents were
        found but the model emitted no `[[source:...]]` marker, append the markers
        (deduped). A no-op when the model already cited, or nothing was found."""
        if not doc_sources or "[[source:" in text:
            return text

        markers, seen = [], set()
        for s in doc_sources:
            key = (str(s["source_id"]), str(s["page_number"]))
            if key in seen:
                continue
            seen.add(key)
            quote = " ".join((s["content"] or "").split()[:8])
            markers.append(f"[[source:{s['source_id']}:{s['page_number']}|{quote}]]")

        if not markers:
            return text
        return f"{text}\n\n**Sources:** " + " ".join(markers)

    def _build_system_prompt(self, bb: BlackBoard) -> str:
        """Base agent contract + conversation summary + (skill) instructions and
        output contract. Non-skill tool contracts are appended during the loop."""
        parts = [agent_prompt]
        if bb.history:
            parts.append("## Conversation so far\n" + bb.history)
        if bb.skill_prompt:
            parts.append("## Skill instructions\n" + bb.skill_prompt)
        if bb.output_contract:
            parts.append(
                "## Output-format contract (match the object SHAPE EXACTLY)\n"
                + bb.output_contract)
        return "\n\n".join(parts)

    def _conversation_history(self) -> str:
        """Summary + recent messages for this session (server-side), so the
        client needn't resend the whole conversation. Empty when there is no
        session yet (first message) or on any read failure."""
        if not self.session_id:
            return ""
        from db.connection import SessionLocal
        from repositories.chat_session_repository import conversation_context_for
        db = SessionLocal()
        try:
            return conversation_context_for(self.session_id, db)
        except Exception:
            print("v3 conversation_history fetch failed")
            return ""
        finally:
            db.close()
