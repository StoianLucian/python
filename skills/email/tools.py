from db.connection import SessionLocal
from db.schemas.user import User
from fastmcp import FastMCP
from import_folder.response import ToolResponse
from services.email import send_email as send_email_service


def register_email_tools(mcp: FastMCP):

    @mcp.tool
    async def send_email(user_id: str, subject: str, content: str) -> ToolResponse:
        """Send email to a specific user."""

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == int(user_id)).first()

            if not user:
                return ToolResponse(success=False, result="User not found")

            send_email_service("lucians@ensemble.com", subject, content)

            return ToolResponse(
                success=True,
                result=f"Email sent successfully to user {user_id}",
            )
        except ValueError:
            return ToolResponse(success=False, result=f"Invalid user id: {user_id}")
        except Exception as e:
            return ToolResponse(success=False, result=str(e))
        finally:
            db.close()
