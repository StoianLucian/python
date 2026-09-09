from skills.base import Skill
from skills.add_exercise.tools import register_exercises_tools


class ExerciseSkill(Skill):
    name = "exercises"
    description = (
        "Track calories burned for exercises the user did, given the exercise "
        "and the amount (repetitions for rep-based exercises, minutes for "
        "duration-based ones)."
    )
    keywords = [
        "exercise",
        "workout",
        "reps",
        "repetitions",
        "pushups",
        "push-ups",
        "squats",
        "running",
        "cardio",
        "burned",
    ]
    trigger = ["/add_exercise"]
    tools = ["lookup_exercise", "add_exercise_entry", "get_exercise_daily_totals"]

    def register(self, mcp):
        register_exercises_tools(mcp)
