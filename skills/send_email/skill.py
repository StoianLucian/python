from skills.base import Skill

from .tools import register_email_tools

# from skills.email.

class EmailSkill(Skill):
    name="email"
    description="Send emails to users"
    keywords=["email", "mail", "gmail", "outlook"]
    tools=["send_email"]
    trigger=['/send_email']
    
    def register(self, mcp):
        register_email_tools(mcp)