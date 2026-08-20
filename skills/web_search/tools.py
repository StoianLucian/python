from fastmcp import FastMCP
from import_folder.response import ToolResponse
import os
from tavily import TavilyClient

from typing import Optional
from pydantic import BaseModel


class WebSearchResult(BaseModel):
    """A single result returned by the Tavily search API."""

    url: str
    title: str
    content: str
    score: float
    id: Optional[str] = None
    raw_content: Optional[str] = None


class WebSearchResponse(BaseModel):
    """The full payload returned by ``TavilyClient.search``."""

    query: str
    results: list[WebSearchResult] = []
    answer: Optional[str] = None
    follow_up_questions: Optional[list[str]] = None
    images: list[str] = []
    response_time: Optional[float] = None
    request_id: Optional[str] = None


def register_web_search_tools(mcp: FastMCP):

    @mcp.tool
    async def web_search(user_query: str) -> ToolResponse[WebSearchResponse]:
        """
            Search the internet for current, real-time, or external information.

            Use this tool whenever the user asks about recent events, news, latest
            versions or prices, external companies/products/people, or anything that
            changes over time or may be outside your training data. Returns the most
            relevant web results (title, url, and a content snippet) to help answer
            the question.

            Args:
                user_query: A concise, keyword-focused search query built from the
                    user's question.
        """
        print("======= web search start")

        try:
            TAVILY_SEARCH_KEY = os.getenv("TAVILY_SEARCH_KEY")
            client = TavilyClient(TAVILY_SEARCH_KEY)
            response = client.search(
                query=user_query,
                search_depth="advanced"
            )

            result = WebSearchResponse.model_validate(response)

            return ToolResponse(success=True, result=result)

        except Exception as e:
            return ToolResponse(success=False, result=f"Error: {e}")
