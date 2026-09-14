import uuid

from sqlalchemy.orm import Session

from app.models.skill import Skill


def list_all(db: Session) -> list[Skill]:
    return db.query(Skill).order_by(Skill.name).all()


def get_by_id(db: Session, skill_id: uuid.UUID) -> Skill | None:
    return db.get(Skill, skill_id)


def get_by_name(db: Session, name: str) -> Skill | None:
    return db.query(Skill).filter(Skill.name.ilike(name)).first()


def get_many_by_ids(db: Session, skill_ids: list[uuid.UUID]) -> list[Skill]:
    if not skill_ids:
        return []
    return db.query(Skill).filter(Skill.id.in_(skill_ids)).all()


def create(db: Session, name: str) -> Skill:
    skill = Skill(name=name)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def update(db: Session, skill_id: uuid.UUID, name: str) -> Skill | None:
    skill = get_by_id(db, skill_id)

    if not skill:
        return None

    skill.name = name
    db.commit()
    db.refresh(skill)

    return skill


def delete(db: Session, skill_id: uuid.UUID) -> Skill | None:
    skill = get_by_id(db, skill_id)

    if not skill:
        return None

    db.delete(skill)
    db.commit()

    return skill