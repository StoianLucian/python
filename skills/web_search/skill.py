import json
from typing import Optional

from skills.base import Skill
from skills.web_search.tools import register_web_search_tools

# How many sources to cite in the response.
MAX_CITED_SOURCES = 5


class WebSearchSkill(Skill):
    name = "web_search"
    description = "Search for information on the internet."
    trigger = ["/web_search"]
    tools = ["web_search"]

    def register(self, mcp):
        register_web_search_tools(mcp)

    def render_response(self, tool_history: list[dict]) -> Optional[list[dict]]:
        """Build the answer from *every* web_search the model ran this turn.

        The model may refine its query and search several times to gather more or
        more-accurate info (see prompt.md). Tavily returns a ready-made synthesized
        `answer` plus ranked sources per call, so we merge those across all calls —
        deduping sources by URL and keeping the highest score — and assemble the
        `text` + `url` objects here instead of asking the small local model to
        re-synthesize them (which it does unreliably).
        """
        payloads = self._web_search_results(tool_history)
        if not payloads:
            return None  # No tool result found — let the model handle it.

        # Any successful search is enough to render; only bail out as failed if
        # every search failed.
        if not any(p.get("success", False) for p in payloads):
            return [{"type": "error",
                     "text": "Sorry, the web search failed. Please try again."}]

        answers: list[str] = []
        merged: dict[str, dict] = {}  # url -> best-scoring result
        for payload in payloads:
            result = payload.get("result") or {}
            answer = (result.get("answer") or "").strip()
            if answer and answer not in answers:
                answers.append(answer)
            for r in (result.get("results") or []):
                url = r.get("url")
                if not url:
                    continue
                if url not in merged or r.get("score", 0) > merged[url].get("score", 0):
                    merged[url] = r

        results = sorted(
            merged.values(), key=lambda r: r.get("score", 0), reverse=True)

        if not answers and not results:
            return [{"type": "error",
                     "text": "I couldn't find anything useful for that. "
                             "Try rephrasing your question."}]

        response: list[dict] = []
        if answers:
            response.append({"type": "text", "text": "\n\n".join(answers)})
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
    def _web_search_results(tool_history: list[dict]) -> list[dict]:
        """Return the parsed structured content of every web_search tool message
        in the order they were called, skipping any that fail to parse."""
        payloads: list[dict] = []
        for msg in tool_history:
            if msg.get("role") == "tool" and msg.get("name") == "web_search":
                try:
                    payloads.append(json.loads(msg.get("content") or ""))
                except (ValueError, TypeError):
                    continue
        return payloads
