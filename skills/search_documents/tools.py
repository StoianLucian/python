from fastmcp import FastMCP
from helpers.helpers import return_document_context
from import_folder.response import ToolResponse

from pydantic import BaseModel

class DocumentSearchResposnse(BaseModel):
    page_number: int
    source_id: int
    content: str

def register_search_documents_tools(mcp: FastMCP):

    @mcp.tool
    async def search_documents(user_query: str, created_by: int) -> ToolResponse[list[DocumentSearchResposnse]]:
        """
            Search the user's OWN knowledge base — the documents, PDFs, notes, and
            images they have uploaded/indexed — for excerpts relevant to the question.

            This is the PRIMARY source for anything about the user's own content.
            Prefer it over web search whenever the question could plausibly be
            answered from stored material: documentation, manuals, policies, guides,
            FAQs, uploaded files, or captioned images — including questions that say
            "my", "the", "this", or name/attach a document. If you are unsure whether
            the answer is in the user's documents, call this tool FIRST and only use
            web search if it returns nothing relevant.

            Do NOT use this for external, public, or real-time information (news,
            prices, latest versions, third-party people/products) — that is web search.

            Args:
                user_query: The user's natural language question or search query.
        """
      
        try:
            # `created_by` is injected server-side from the authenticated user
            # (see USER_SCOPED_TOOLS) and stripped from the schema shown to the
            # model, so search only ever sees the current user's own documents.
            context = return_document_context(user_query, created_by)

            return ToolResponse(success=True, result=context)

        except Exception as e:
            return ToolResponse(success=False, result="Error: {e}}")
