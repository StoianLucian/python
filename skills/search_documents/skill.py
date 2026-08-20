from skills.base import Skill
from skills.search_documents.tools import register_search_documents_tools


# from skills.email.

class SearchDocumentsSkill(Skill):
    name = "search_documents"
    description = "Search for information in stored documents."
    keywords = [
        # Documentation
        # "documentation",
        # "docs",
        # "manual",
        # "guide",
        # "wiki",
        # "knowledge base",
        # "kb",

        # # Instructions
        # "how to",
        # "how do i",
        # "steps",
        # "instructions",

        # # Policies / procedures
        # "policy",
        # "procedure",
        # "process",
        # "standard",
        # "requirements",

        # # Looking for information
        # "where",
        # "find",
        # "lookup",
        # "search",
        # "information",
        # "reference",

        # # Questions
        # "what is",
        # "can i",
        # "does",
        # "when",
        # "who",
    ]
    trigger = ["/search_documents"]
    tools = ["search_documents"]
    
    def register(self, mcp):
        register_search_documents_tools(mcp)