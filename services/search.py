import os
from typing import Optional, Union

from tavily import TavilyClient


def search_web(
    query: str,
    max_results: Optional[int] = 5,
    search_depth: Optional[str] = "advanced",
    include_answer: Union[bool, str] = "advanced",
) -> Optional[dict]:
    """Single Tavily search wrapper, reused by every feature that needs the web
    (the /web_search skill, calorie and exercise lookups).

    Returns the raw Tavily response dict with `results` sorted by score (highest
    first) and an LLM-written `answer` summary when `include_answer` is set, or
    None on failure. Callers pick what they need (`answer`, `results`, ...).
    """
    api_key = os.getenv("TAVILY_SEARCH_KEY")
    if not api_key:
        print("[search_web] TAVILY_SEARCH_KEY not set; cannot web-search")
        return None

    if not query:
        print("[search_web] query not provided; cannot web-search")
        return None

    try:
        client = TavilyClient(api_key)
        # Pass by keyword — Tavily's second positional arg is `topic`, not
        # `max_results`, so positional args silently send the wrong parameters.
        response = client.search(
            query=query,
            search_depth=search_depth,
            max_results=max_results,
            include_answer=include_answer,
        )

        response["results"] = sorted(
            response.get("results", []),
            key=lambda r: r.get("score", 0),
            reverse=True,
        )
        return response

    except Exception as e:
        print(f"[search_web] web search failed: {e}")
        return None
