from skills.base import Skill
from skills.add_calories.tools import register_calorie_tools


class CaloriesSkill(Skill):
    name = "add exercises"
    description = (
        "Track calories and macros (protein, carbs, fat) for foods the user "
        "eats, given the food and the amount in grams."
    )
    keywords = [
        "calories",
        "calorie",
        "kcal",
        "macros",
        "protein",
        "carbs",
        "fat",
        "ate",
        "eat",
    ]
    trigger = ["/add_exercise"]
    # tools = ["lookup_exercise", "add_exercise_entry", "get_daily_totals_tool"]
    tools = ["lookup_exercise"]

    def register(self, mcp):
        register_calorie_tools(mcp)
