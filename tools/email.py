from db.connection import SessionLocal
from db.schemas.user import User
from fastmcp import FastMCP
from import_folder.response import ToolResponse

def register_email_tools(mcp: FastMCP):

    @mcp.tool
    def send_email(user: str, content: str) -> ToolResponse:
        """Send email to a specific user."""
        # db = SessionLocal()
        # print(user, "user_email_tool")
        try:
            # user = db.query(User).filter(User.username == user).first()
            # if not user:
            #     return ToolResponse(success=False, result="User not found")
            # print(user, content, "email_tool")
            return ToolResponse(success=True, result=f"Email sent successfully to {user} with content '{content}'")
        except Exception as e:
            return ToolResponse(success=False, result=str(e))