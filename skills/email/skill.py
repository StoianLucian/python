from skills.base import Skill
from .tools import register_email_tools

# from skills.email.

class EmailSkill(Skill):

    name = "email"
    description = "Send emails"
    tools= ["search_users", "send_email"]
    
    def register(self, mcp):
        register_email_tools(mcp)
        
    def prompt(self):
        with open("skills/email/prompt.md") as f:
            return f.read()
    def examples(self):
        with open("skills/email/examples.md") as f:
            return f.read()