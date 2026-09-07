import json
from typing import Optional

from skills.base import Skill
from skills.web_search.tools import register_web_search_tools

# How many sources to cite in the response.
MAX_CITED_SOURCES = 5


class WebSearchSkill(Skill):
    name = "web_search"
    description = "Search for information on the internet."
    keywords = [

    ]
    trigger = ["/web_search"]
    tools = ["web_search"]

    def register(self, mcp):
        register_web_search_tools(mcp)

    def render_response(self, tool_history: list[dict]) -> Optional[list[dict]]:
        """Build the answer directly from the last web_search tool result.

        Tavily returns a ready-made synthesized `answer` plus ranked sources, so
        we assemble the `text` + `url` objects here instead of asking the small
        local model to re-synthesize them (which it does unreliably).
        """
        payload = self._last_web_search_result(tool_history)
        if payload is None:
            return None  # No tool result found — let the model handle it.

        if not payload.get("success", False):
            return [{"type": "error",
                     "text": "Sorry, the web search failed. Please try again."}]

        result = payload.get("result") or {}
        answer = (result.get("answer") or "").strip()
        results = [r for r in (result.get("results") or []) if r.get("url")]

        if not answer and not results:
            return [{"type": "error",
                     "text": "I couldn't find anything useful for that. "
                             "Try rephrasing your question."}]

        response: list[dict] = []
        if answer:
            response.append({"type": "text", "text": answer})
        else:
            # No synthesized answer — fall back to the top snippet.
            response.append({"type": "text", "text": results[0].get("content", "")})

        for r in results[:MAX_CITED_SOURCES]:
            response.append({
                "type": "url",
                "text": (r.get("title") or r["url"])[:60],
                "url": r["url"],
            })

        return response

    @staticmethod
    def _last_web_search_result(tool_history: list[dict]) -> Optional[dict]:
        """Return the parsed structured content of the most recent web_search
        tool message, or None if there isn't one."""
        for msg in reversed(tool_history):
            if msg.get("role") == "tool" and msg.get("name") == "web_search":
                try:
                    return json.loads(msg.get("content") or "")
                except (ValueError, TypeError):
                    return None
        return None
