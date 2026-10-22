from fastmcp import FastMCP
from import_folder.response import ToolResponse

from typing import Optional
from pydantic import BaseModel

from services.search import search_web


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
    async def web_search(user_query: str) -> ToolResponse:
        """
            Search the public internet for EXTERNAL, current, or real-time
            information that is NOT in the user's own documents.

            Use this only for recent events, news, latest versions or prices,
            third-party companies/products/people, or anything that changes over time
            or is outside both your training data and the user's knowledge base.

            Do NOT use this for the user's own uploaded/indexed content — their files,
            documents, notes, or images. For that, use `document_search` first; only
            fall back to web search if the documents do not contain the answer.
            Returns the most relevant web results (title, url, and a content snippet).

            Args:
                user_query: A concise, keyword-focused search query built from the
                    user's question.
        """
        print("======= web search start")

        try:
            response = search_web(user_query)
            if response is None:
                return ToolResponse(
                    success=False,
                    result="Web search is unavailable right now.",
                )

            result = WebSearchResponse(
                query=response.get("query", user_query),
                answer=response.get("answer"),
                results=[
                    WebSearchResult(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        content=r.get("content", ""),
                        score=r.get("score", 0.0),
                    )
                    for r in response.get("results", [])
                ],
            )

            return ToolResponse(success=True, result=result)

        except Exception as e:
            return ToolResponse(success=False, result=f"Error: {e}")
