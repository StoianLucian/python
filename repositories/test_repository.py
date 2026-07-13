
from fastmcp import FastMCP
from sqlalchemy.orm import Session
from db.schemas.user import User

mcp = FastMCP("Assistant")

from db.connection import SessionLocal, get_db

@mcp.tool
def get_test(city: str) -> str:
    
    # db = SessionLocal()
    # db.query(User).all()
    print(city, "get_weather")
    
    return f"It's sunny in {city}."