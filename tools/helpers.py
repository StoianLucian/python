from typing import Optional, Type

from requests import Session


def find_skill(query: str):
    # Imported lazily to avoid a circular import: skills/__init__.py imports
    # skill modules that (transitively) import this module.
    from skills import AVAILABLE_SKILLS

    # Match only on a skill's explicit trigger commands.
    for skill in AVAILABLE_SKILLS:
        if any(k in query for k in skill.trigger):
            return skill

    return None


def skill_for_tool(tool_name: str):
    """Return the skill that owns ``tool_name`` (first match), or None.

    Lets the chat loop find a tool's response-format contract even when the tool
    was chosen by the model rather than via an explicit skill mention."""
    from skills import AVAILABLE_SKILLS

    for skill in AVAILABLE_SKILLS:
        if tool_name in skill.tools:
            return skill
    return None


def strip_trigger(query: str, skill) -> str:
    """Remove any of the skill's trigger tokens from the message and trim."""
    cleaned = query
    for t in skill.trigger:
        cleaned = cleaned.replace(t, "")
    return cleaned.strip()


def get_category_name(db: Session, category_id: Optional[int], entity_type: Type) -> Optional[str]:
    """Return the category name for an id, or None."""
    if category_id is None:
        return None
    category = db.get(entity_type, category_id)
    return category.name if category else None
