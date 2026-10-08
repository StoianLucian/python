from skills.base import Skill
from skills.search_documents.tools import register_search_documents_tools


# from skills.email.

class SearchDocumentsSkill(Skill):
    name = "search_documents"
    description = "Search for information in stored documents."
    trigger = ["/search_documents"]
    tools = ["search_documents"]
    
    def register(self, mcp):
        register_search_documents_tools(mcp)