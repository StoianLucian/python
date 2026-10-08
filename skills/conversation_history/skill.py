from skills.base import Skill
from skills.conversation_history.tools import register_conversation_history_tools


class ConversationHistorySkill(Skill):
    name = "conversation_history"
    description = "Recall earlier messages from the current conversation."
    trigger = ["/history"]
    tools = ["get_conversation_history"]

    def register(self, mcp):
        register_conversation_history_tools(mcp)
