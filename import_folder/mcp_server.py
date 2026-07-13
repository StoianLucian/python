
from fastmcp import FastMCP

mcp = FastMCP("Assistant")


from tools.email import register_email_tools
from tools.weather import register_weather_tools
from tools.users import register_users_tools
from tools.serach_documents import register_document_search_tools

register_weather_tools(mcp)
register_email_tools(mcp)
register_users_tools(mcp)
register_document_search_tools(mcp)


mcp_app = mcp.http_app(path="/")