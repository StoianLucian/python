# skills/__init__.py

from skills.total_calories.skill import TotalCalorisSkill
from skills.send_email.skill import EmailSkill
from skills.search_documents.skill import SearchDocumentsSkill
from skills.base import Skill
from skills.web_search.skill import WebSearchSkill
from skills.add_calories.skill import CaloriesSkill
from skills.add_exercise.skill import ExerciseSkill
from skills.conversation_history.skill import ConversationHistorySkill
from skills.execute_sql.skill import ExecuteSqlSkill

AVAILABLE_SKILLS: list[Skill] = [
    EmailSkill(),
    SearchDocumentsSkill(),
    WebSearchSkill(),
    CaloriesSkill(),
    TotalCalorisSkill(),
    ExerciseSkill(),
    ConversationHistorySkill(),
    ExecuteSqlSkill(),
]
