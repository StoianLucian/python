from skills.base import Skill


class TotalCalorisSkill(Skill):
    name = "total_calories"
    description = (
        "returns the total calories consumed for the entire day"
    )
    keywords = [
        "total caloris"
    ]
    trigger = ["/total_calories"]
    tools = ["get_daily_totals_tool"]
