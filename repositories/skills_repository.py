
from datetime import datetime

from sqlalchemy.orm import Session, load_only
from db.schemas.skill import Skill

def populate_skills(db: Session):
    print("populate_skills")
    try:
        
        skills = [
            Skill(name="Send Email", key="send_email", created_at=datetime.now()),
            Skill(name="Send SMS", key="send_sms", created_at=datetime.now()),
            Skill(name="Generate Report", key="generate_report", created_at=datetime.now()),
            Skill(name="Create Task", key="create_task", created_at=datetime.now()),
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
    else :
        skills = db.query(Skill).all()

    return skills

