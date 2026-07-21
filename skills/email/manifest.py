from dataclasses import dataclass

@dataclass
class SkillManifest:
    name:str
    description:str
    keywords: list[str]
    tools: list[str]
    
manifest = SkillManifest(
    name="email", 
    description="Send emails to company users",
    keywords=["email", "mail", "gmail", "outlook"], 
    tools=["search_users", "send_email"]
    )