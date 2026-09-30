from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from ..db import get_db
from ..models import Skill, SkillAlias
from ..schemas import SkillBase

router = APIRouter(prefix="/api/skills", tags=["skills"])

@router.get("", response_model=List[SkillBase])
def get_skills(db: Session = Depends(get_db)):
    skills = db.query(Skill).all()
    results = []
    for skill in skills:
        aliases = [a.alias for a in db.query(SkillAlias).filter(SkillAlias.skill_id == skill.id).all()]
        results.append({
            "id": skill.id,
            "name": skill.name,
            "category": skill.category,
            "aliases": aliases
        })
    return results
