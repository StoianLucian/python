from skills.base import Skill
from skills.add_calories.tools import register_calorie_tools


class CaloriesSkill(Skill):
    name = "calories"
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
    trigger = ["/add_calories"]
    tools = ["lookup_product", "add_food_entry", "get_daily_totals_tool"]

    def register(self, mcp):
        register_calorie_tools(mcp)
