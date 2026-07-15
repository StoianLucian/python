from db.connection import SessionLocal
from fastmcp import FastMCP
from db.schemas.user import User
from helpers.helpers import return_context_2
from import_folder.response import ToolResponse
from schemas.user_schemas import UserBase

def register_document_search_tools(mcp: FastMCP):

    @mcp.tool
    async def document_search(user_query: str) -> ToolResponse[str]:
        """
            Search the knowledge base for documents relevant to the user's question.

            Use this tool whenever the user asks about information that may exist in stored
            documentation, manuals, policies, guides, FAQs, or previously indexed documents.
            The tool retrieves the most relevant document excerpts to help answer the question.

            Args:
                user_query: The user's natural language question or search query.
        """
      
        try:
            context = return_context_2(user_query)
            
            print(context, "context")
            
            return ToolResponse(success=True, result=context)

        except Exception as e:
            return ToolResponse(success=False, result="Error: {e}}")
        
        
        # db = SessionLocal()
        # try:
        #     # users = db.query(User).all()
            
        #     # db_users = []
            
        #     # for user in users:
        #     #     db_users.append({
        #     #         "username": user.username,
        #     #         "email": user.email
        #     #     })
            
        #     return ToolResponse(success=True, result=db_users)
        # except Exception as e:
        #     return ToolResponse(success= False, result=f"Error: {e}")
        # finally:
        #     db.close()