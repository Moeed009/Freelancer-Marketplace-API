from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.repositories import skill_repository
from app.schemas.skill import SkillUpdate


def list_skills(db: Session) -> list:
    return skill_repository.list_all(db)


def create_skill(db: Session, name: str):
    normalized = name.strip()

    if skill_repository.get_by_name(db, normalized):
        raise ConflictError("This skill already exists.")

    return skill_repository.create(db, normalized)


def update_skill(db: Session, skill_id, payload: SkillUpdate):
    normalized = payload.name.strip()

    existing_skill = skill_repository.get_by_name(db, normalized)

    if existing_skill and existing_skill.id != skill_id:
        raise ConflictError("This skill already exists.")

    return skill_repository.update(
        db,
        skill_id,
        normalized
    )


def delete_skill(db: Session, skill_id):
    return skill_repository.delete(db, skill_id)