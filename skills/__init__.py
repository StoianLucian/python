# skills/__init__.py

from skills.email.skill import EmailSkill
from skills.search_documents.skill import SearchDocumentsSkill
from skills.base import Skill

AVAILABLE_SKILLS:list[Skill] = [
    EmailSkill(),
    SearchDocumentsSkill()
]