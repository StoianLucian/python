"""Experimental multi-agent chat path (`/chat/v3`).

An Orchestrator drives five specialized sub-agents (Planner, Selector, Observer,
Evaluator, Answerer/Clarifier) over a shared BlackBoard. Unlike the single-loop
v1/v2 paths, there is no shared growing message history: each sub-agent turn is
built fresh from a role prompt plus a scoped *projection* of the blackboard.

See /Users/lucians/.claude/plans/would-using-multiple-agent-shimmering-ember.md
"""

from agents.blackboard import BlackBoard, ToolCallRecord
from agents.orchestrator import Orchestrator

__all__ = ["BlackBoard", "ToolCallRecord", "Orchestrator"]
