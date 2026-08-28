# skills/__init__.py

from skills.total_calories.skill import TotalCalorisSkill
from skills.send_email.skill import EmailSkill
from skills.search_documents.skill import SearchDocumentsSkill
from skills.base import Skill
from skills.user_list.skill import UserListSkill
from skills.web_search.skill import WebSearchSkill
from skills.add_calories.skill import CaloriesSkill

AVAILABLE_SKILLS: list[Skill] = [
    EmailSkill(),
    SearchDocumentsSkill(),
    UserListSkill(),
    WebSearchSkill(),
    CaloriesSkill(),
    TotalCalorisSkill()
]
