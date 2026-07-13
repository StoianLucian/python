from typing import Any

from db.connection import SessionLocal
from fastmcp import FastMCP
from db.schemas.user import User
from pydantic import BaseModel

class WeatherResponse(BaseModel):
    success: bool
    result: str

def register_weather_tools(mcp: FastMCP):

    @mcp.tool
    async def get_weather(city: str) -> WeatherResponse:
        
        db = SessionLocal()
        try:
            users = db.query(User).all()
            
            print("print users", users)
            
            return WeatherResponse(success=True, result=f"weather is nice in {city}")
        except Exception as e:
            print(e)
            return WeatherResponse(success=False, result=f"Error: {e}")
        finally:
            db.close()