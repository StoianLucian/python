from skills.base import Skill
from tools.users import register_users_tools


class UserListSkill(Skill):
    name = "user_list"
    description = "Return a list of all users."
    keywords = [
        "list of users"
    ]
    trigger = ["/users_list"]
    tools = ["get_all_users"]

    def register(self, mcp):
        register_users_tools(mcp)
