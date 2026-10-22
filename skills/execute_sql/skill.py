from skills.base import Skill
from skills.execute_sql.tools import register_execute_sql_tools


class ExecuteSqlSkill(Skill):
    name = "execute_sql"
    description = (
        "Answer data questions by running a read-only SQL SELECT against the "
        "application database (users, chat sessions/messages, files, chunks, "
        "food and exercise entries, catalogs, etc.)."
    )
    trigger = ["/execute_sql"]
    tools = ["execute_sql"]
    # Powerful, general tool — don't offer it by default (the model over-calls
    # it). Only available when the user explicitly invokes /execute_sql.
    explicit_only = True

    def register(self, mcp):
        register_execute_sql_tools(mcp)
