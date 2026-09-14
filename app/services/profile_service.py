import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.enums import AvailabilityStatus
from app.repositories import freelancer_profile_repository, skill_repository
from app.schemas.freelancer_profile import FreelancerProfileCreate, FreelancerProfileUpdate


def get_my_profile(db: Session, user_id: uuid.UUID):
    profile = freelancer_profile_repository.get_by_user_id(db, user_id)
    if profile is None:
        raise NotFoundError("Freelancer profile not found. Create one first.")
    return profile


def get_public_profile(db: Session, user_id: uuid.UUID):
    profile = freelancer_profile_repository.get_by_user_id(db, user_id)
    if profile is None:
        raise NotFoundError("Freelancer profile not found.")
    return profile


def delete_profile(db: Session, user_id: uuid.UUID) -> None:
    profile = get_my_profile(db, user_id)
    freelancer_profile_repository.delete(db, profile)


def search_profiles(
    db: Session,
    *,
    keyword: str | None,
    skill_id: uuid.UUID | None,
    availability: AvailabilityStatus | None,
    offset: int,
    limit: int,
):
    return freelancer_profile_repository.search(
        db,
        keyword=keyword,
        skill_id=skill_id,
        availability=availability,
        offset=offset,
        limit=limit,
    )


def _validate_skill_ids(db: Session, skill_ids: list[uuid.UUID]) -> None:
    if not skill_ids:
        return
    found = skill_repository.get_many_by_ids(db, skill_ids)
    if len(found) != len(set(skill_ids)):
        raise ValidationAppError("One or more skill_ids do not exist.")


def create_profile(db: Session, user_id: uuid.UUID, data: FreelancerProfileCreate):
    if freelancer_profile_repository.get_by_user_id(db, user_id):
        raise ConflictError("Freelancer profile already exists for this user. Use update instead.")

    fields = data.model_dump(exclude_unset=True, exclude={"skill_ids"})
    skill_ids = data.skill_ids
    _validate_skill_ids(db, skill_ids)

    profile = freelancer_profile_repository.create(db, user_id=user_id, **fields)
    return freelancer_profile_repository.replace_skills(db, profile, skill_ids)


def update_profile(db: Session, user_id: uuid.UUID, data: FreelancerProfileUpdate):
    """True partial update: any field the client didn't include in the
    request body (exclude_unset) is left completely untouched. skill_ids
    only gets replaced if the client explicitly included it - sending
    skill_ids: [] clears all skills, omitting it entirely leaves the
    existing skills as-is."""
    profile = get_my_profile(db, user_id)

    fields = data.model_dump(exclude_unset=True, exclude={"skill_ids"})
    if fields:
        profile = freelancer_profile_repository.update(db, profile, **fields)

    if "skill_ids" in data.model_fields_set and data.skill_ids is not None:
        _validate_skill_ids(db, data.skill_ids)
        profile = freelancer_profile_repository.replace_skills(db, profile, data.skill_ids)

    return profile


def set_skills(db: Session, user_id: uuid.UUID, skill_ids: list[uuid.UUID]):
    profile = get_my_profile(db, user_id)
    _validate_skill_ids(db, skill_ids)
    return freelancer_profile_repository.replace_skills(db, profile, skill_ids)