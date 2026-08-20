from skills.base import Skill
from skills.web_search.tools import register_web_search_tools


class WebSearchSkill(Skill):
    name = "web_search"
    description = "Search for information on the internet."
    keywords = [

    ]
    trigger = ["/web_search"]
    tools = ["web_search"]

    def register(self, mcp):
        register_web_search_tools(mcp)
