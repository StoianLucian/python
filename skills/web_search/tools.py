from db.connection import SessionLocal
from fastmcp import FastMCP
from db.schemas.user import User
from helpers.helpers import return_context_2
from import_folder.response import ToolResponse

from pydantic import BaseModel

class DocumentSearchResposnse(BaseModel):
    page_number: int
    source_id: int
    content: str

def register_web_search_tools(mcp: FastMCP):

    @mcp.tool
    async def search_documents(user_query: str) -> ToolResponse[list[DocumentSearchResposnse]]:
        """
            Search the knowledge base for documents relevant to the user's question.

            Use this tool whenever the user asks about information that may exist in stored
            documentation, manuals, policies, guides, FAQs, or previously indexed documents.
            The tool retrieves the most relevant document excerpts to help answer the question.

            Args:
                user_query: The user's natural language question or search query.
        """
        
        print("try============")
      
        try:
            context = return_context_2(user_query)
            
            return ToolResponse(success=True, result=context)

        except Exception as e:
            return ToolResponse(success=False, result="Error: {e}}")
