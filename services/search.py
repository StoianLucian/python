import os
from typing import Optional
from tavily import TavilyClient


def search_seb(query: str) -> Optional[dict]:
    """Search the web for exercise calories consumtion per repetion or time"""
    api_key = os.getenv("TAVILY_SEARCH_KEY")
    if not api_key:
        print("[_search_exercise_calories] TAVILY_SEARCH_KEY not set; cannot web-search")
        return None

    try:
        client = TavilyClient(api_key)
        response = client.search(
            query=f"{query} nutrition facts per 100g calories protein carbs fat",
            search_depth="advanced",
            max_results=5,
        )
        print(response, "response product search ===========")
    except Exception as e:
        print(f"[lookup_product] web search failed: {e}")
        return None
