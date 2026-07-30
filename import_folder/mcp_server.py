
from fastmcp import FastMCP

mcp = FastMCP("Assistant")

from skills import AVAILABLE_SKILLS

for skill_cls in AVAILABLE_SKILLS:
    skill_cls.register(mcp=mcp)


mcp_app = mcp.http_app(path="/")