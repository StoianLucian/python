# skills/__init__.py

from skills.email.skill import EmailSkill
from skills.search_documents.skill import SearchDocumentsSkill
from skills.base import Skill
from skills.user_list.skill import UserListSkill
from skills.web_search.skill import WebSearchSkill

AVAILABLE_SKILLS:list[Skill] = [
    EmailSkill(),
    SearchDocumentsSkill(),
    UserListSkill(),
    WebSearchSkill()
]