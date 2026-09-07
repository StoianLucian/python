
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session, load_only
from db.schemas.skill import Skill
from errors.user import SkillAlreadyExistsError
from schemas import SkillCreate


def populate_skills(db: Session):
    print("populate_skills")
    try:

        skills = [
            Skill(name="Send Email", key="send_email",
                  created_at=datetime.now()),
            Skill(name="Send SMS", key="send_sms", created_at=datetime.now()),
            Skill(name="Generate Report", key="generate_report",
                  created_at=datetime.now()),
            Skill(name="Create Task", key="create_task",
                  created_at=datetime.now()),
        ]

        db.add_all(skills)
        db.commit()

        return f"Added {len(skills)} skills."
    except Exception as e:
        print("Skills error")
        raise e


def get_skills_db(db: Session, search: str):

    if search is not None and search != "":
        skills = db.query(Skill).filter(Skill.name.ilike(f"%{search}%")).all()
    else:
        skills = db.query(Skill).all()

    return skills


def create_skill_db(skillData: SkillCreate, db: Session):
    existing = db.query(Skill).filter(
        or_(Skill.name == skillData.name, Skill.key == skillData.key)
    ).first()

    if existing is not None:
        raise SkillAlreadyExistsError()

    skill = Skill(
        name=skillData.name,
        key=skillData.key,
        created_at=datetime.now(),
    )

    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill
