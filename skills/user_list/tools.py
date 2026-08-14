from db.connection import SessionLocal
from fastmcp import FastMCP
from db.schemas.user import User
from import_folder.response import ToolResponse
from schemas.user_schemas import UserBase
from sqlalchemy import or_


from pydantic import BaseModel


class Users(BaseModel):
    id: int
    email: str


def register_users_tools(mcp: FastMCP):

    @mcp.tool
    async def get_all_users() -> ToolResponse[list[Users]]:
        """
        Retrieve all available users with their id and email adress.

        Use this tool whenever you need to fetch all users
        """
        db = SessionLocal()
        try:
            users = db.query(User).all()

            db_users = []

            for user in users:
                db_users.append({
                    "username": user.username,
                    "email": user.email,
                    "id": user.id
                })

            return ToolResponse(success=True, result=db_users)
        except Exception as e:
            return ToolResponse(success=False, result=f"Error: {e}")
        finally:
            db.close()

    @mcp.tool
    async def get_users_by_email(identifier: list[str]) -> ToolResponse[list[UserBase]]:
        """
        Retrieve all available users with their usernames and email addresses.

        Use this tool whenever you need to identify a user's username before calling another tool.
        """
        db = SessionLocal()
        try:
            users = (
                db.query(User)
                .filter(
                    or_(
                        User.email.in_(identifier),
                        User.username.in_(identifier),
                    )
                )
                .all()
            )
            db_users = []

            for user in users:
                db_users.append({
                    "username": user.username,
                    "email": user.email
                })

            return ToolResponse(success=True, result=db_users)
        except Exception as e:
            return ToolResponse(success=False, result=f"Error: {e}")
        finally:
            db.close()
