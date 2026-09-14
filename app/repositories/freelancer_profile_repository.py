import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import AvailabilityStatus
from app.models.freelancer_profile import FreelancerProfile
from app.models.freelancer_skill import FreelancerSkill


def get_by_user_id(db: Session, user_id: uuid.UUID) -> FreelancerProfile | None:
    return db.query(FreelancerProfile).filter(FreelancerProfile.user_id == user_id).first()


def delete(db: Session, profile: FreelancerProfile) -> None:
    db.delete(profile)
    db.commit()


def search(
    db: Session,
    *,
    keyword: str | None,
    skill_id: uuid.UUID | None,
    availability: AvailabilityStatus | None,
    offset: int,
    limit: int,
) -> tuple[list[FreelancerProfile], int]:
    query = select(FreelancerProfile)

    if keyword:
        like = f"%{keyword}%"
        query = query.where(FreelancerProfile.headline.ilike(like) | FreelancerProfile.bio.ilike(like))
    if availability is not None:
        query = query.where(FreelancerProfile.availability == availability)
    if skill_id is not None:
        query = query.join(
            FreelancerSkill, FreelancerSkill.freelancer_profile_id == FreelancerProfile.id
        ).where(FreelancerSkill.skill_id == skill_id)

    count_query = select(func.count()).select_from(query.with_only_columns(FreelancerProfile.id).subquery())
    total = db.execute(count_query).scalar_one()

    query = query.order_by(FreelancerProfile.created_at.desc()).offset(offset).limit(limit)
    items = db.execute(query).scalars().unique().all()
    return list(items), total


def create(db: Session, user_id: uuid.UUID, **fields) -> FreelancerProfile:
    profile = FreelancerProfile(user_id=user_id, **fields)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update(db: Session, profile: FreelancerProfile, **fields) -> FreelancerProfile:
    for key, value in fields.items():
        if value is not None:
            setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


def replace_skills(db: Session, profile: FreelancerProfile, skill_ids: list[uuid.UUID]) -> FreelancerProfile:
    db.query(FreelancerSkill).filter(FreelancerSkill.freelancer_profile_id == profile.id).delete()
    for skill_id in set(skill_ids):
        db.add(FreelancerSkill(freelancer_profile_id=profile.id, skill_id=skill_id))
    db.commit()
    db.refresh(profile)
    return profile