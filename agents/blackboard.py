"""The shared state the Orchestrator owns, plus the per-role projections.

The projections are the heart of the experiment: each sub-agent only receives
the slice of state its role needs, instead of the full growing conversation that
v1/v2 use. The table in the plan maps role -> what it sees. Keeping these as
small string builders makes the context scoping explicit and easy to inspect.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
import json


@dataclass
class ToolCallRecord:
    """One executed tool call and its raw structured result."""
    name: str
    arguments: dict
    result: Any
    elapsed: float
    ok: bool = True


@dataclass
class BlackBoard:
    user_request: str
    # Prior conversation turns, pre-formatted as "role: content" lines (bounded).
    # Given to the agents that need conversational context (Planner, Answerer,
    # Clarifier) so follow-up questions resolve; task-local agents (Selector,
    # Observer, Evaluator) don't see it.
    history: str = ""
    skill_name: Optional[str] = None
    skill_prompt: str = ""
    output_contract: str = ""
    allowed_tool_names: list[str] = field(default_factory=list)

    plan: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    verdict: Optional[str] = None
    iteration: int = 0

    # --- helpers ---------------------------------------------------------

    @staticmethod
    def _numbered(items: list[str]) -> str:
        return "\n".join(f"{i}. {t}" for i, t in enumerate(items, 1)) or "(none yet)"

    @staticmethod
    def _dump(result: Any, max_chars: int) -> str:
        dumped = json.dumps(result, default=str)
        if len(dumped) > max_chars:
            return dumped[:max_chars] + "...(truncated)"
        return dumped

    @property
    def objective(self) -> str:
        """The current objective is the latest plan step, or the raw request
        before the Planner has run."""
        return self.plan[-1] if self.plan else self.user_request

    # --- projections: exactly what each role is allowed to see -----------

    def planner_view(self) -> str:
        return (
            f"User request:\n{self.user_request}\n\n"
            f"Plan so far:\n{self._numbered(self.plan)}\n\n"
            f"Observations so far:\n{self._numbered(self.observations)}\n\n"
            f"Last evaluation: {self.verdict or '(none)'}"
        )

    def selector_view(self) -> str:
        last_obs = self.observations[-1] if self.observations else "(none yet)"
        return (
            f"Current objective:\n{self.objective}\n\n"
            f"Most recent observation:\n{last_obs}"
        )

    def observer_view(self, new_calls: list[ToolCallRecord], max_chars: int = 2000) -> str:
        blocks = [f"- {rec.name} -> {self._dump(rec.result, max_chars)}"
                  for rec in new_calls]
        results = "\n".join(blocks) or "(no tool results)"
        return (
            f"Objective these results served:\n{self.objective}\n\n"
            f"Raw tool results:\n{results}"
        )

    def evaluator_view(self) -> str:
        return (
            f"User request:\n{self.user_request}\n\n"
            f"Plan so far:\n{self._numbered(self.plan)}\n\n"
            f"Observations so far:\n{self._numbered(self.observations)}"
        )

    def answerer_view(self, max_chars: int = 4000) -> str:
        blocks = [
            f"- {rec.name}({json.dumps(rec.arguments)}) -> {self._dump(rec.result, max_chars)}"
            for rec in self.tool_calls
        ]
        results = "\n".join(blocks) or "(no tools were used)"
        return (
            f"User request:\n{self.user_request}\n\n"
            f"Observations:\n{self._numbered(self.observations)}\n\n"
            "Raw tool results (use these VERBATIM for any values or citations):\n"
            f"{results}"
        )

    def clarifier_view(self) -> str:
        return (
            f"User request:\n{self.user_request}\n\n"
            f"Observations so far:\n{self._numbered(self.observations)}"
        )

    def tool_history(self) -> list[dict]:
        """Rebuild the tool-message list a skill's `render_response` expects:
        `{"role": "tool", "name": ..., "content": <json string>}` per call. Built
        directly (not via a provider) so it is provider-agnostic."""
        return [
            {"role": "tool", "name": rec.name,
             "content": json.dumps(rec.result, default=str)}
            for rec in self.tool_calls
        ]
