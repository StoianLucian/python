import os
from typing import Optional
from tavily import TavilyClient


def search_web(query: str, max_results: Optional[int] = 5, search_depth: Optional[str] = "advance") -> Optional[dict]:
    """Search the web for exercise calories consumtion per repetion or time"""
    api_key = os.getenv("TAVILY_SEARCH_KEY")
    if not api_key:
        print("[search_web] TAVILY_SEARCH_KEY not set; cannot web-search")
        return None

    if not query:
        print("[search_web] query not provided; cannot web-search")
        return None

    try:
        client = TavilyClient(api_key)
        response = client.search(
            query,
            search_depth,
            max_results,
        )

        print(response, "response web search ===========")
        results = sorted(
            response.get("results", []),
            key=lambda r: r.get("score", 0),
            reverse=True,
        )
        return results

    except Exception as e:
        print(f"[web_search] web search failed: {e}")
        return None
