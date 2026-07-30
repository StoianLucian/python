from skills import AVAILABLE_SKILLS

def find_skill(query: str):
    # 1. Explicit commands
    for skill in AVAILABLE_SKILLS:
        if any(k in query for k in skill.trigger):
            return skill

    # 2. Keyword matching
    query = query.lower()
    for skill in AVAILABLE_SKILLS:
        if any(k in query for k in skill.keywords):
            return skill

    return None