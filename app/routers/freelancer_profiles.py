import math
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import require_freelancer
from app.dependencies.pagination import PaginationParams
from app.models.enums import AvailabilityStatus
from app.models.freelancer_profile import FreelancerProfile
from app.models.user import User
from app.schemas.common import Page
from app.schemas.freelancer_profile import (
    FreelancerProfileCreate,
    FreelancerProfileOut,
    FreelancerProfileUpdate,
)
from app.services import profile_service

router = APIRouter(prefix="", tags=["Freelancer Profiles"])


def _serialize(profile: FreelancerProfile) -> FreelancerProfileOut:
    out = FreelancerProfileOut.model_validate(profile)
    out.skills = [fs.skill for fs in profile.freelancer_skills]
    return out


@router.post("/Create my freelancer profile", response_model=FreelancerProfileOut, status_code=status.HTTP_201_CREATED, summary="Create my freelancer profile (one per user)")
def create_my_profile(payload: FreelancerProfileCreate, current_user: User = Depends(require_freelancer), db: Session = Depends(get_db)):
    profile = profile_service.create_profile(db, current_user.id, payload)
    return _serialize(profile)


@router.get("/own_freelancer_profile", response_model=FreelancerProfileOut, summary="Get my own freelancer profile")
def get_my_profile(current_user: User = Depends(require_freelancer), db: Session = Depends(get_db)):
    profile = profile_service.get_my_profile(db, current_user.id)
    return _serialize(profile)


@router.get(
    "/search_freelancer_profiles",
    response_model=Page[FreelancerProfileOut],
    summary="Browse/search freelancer profiles (any authenticated or public visitor - CLIENT use case)",
)
def search_freelancer_profiles(
    keyword: str | None = Query(default=None, description="Matches against headline/bio"),
    skill_id: uuid.UUID | None = Query(default=None),
    availability: AvailabilityStatus | None = Query(default=None),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    items, total = profile_service.search_profiles(
        db,
        keyword=keyword,
        skill_id=skill_id,
        availability=availability,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    return Page(
        items=[_serialize(p) for p in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=math.ceil(total / pagination.page_size) if total else 0,
    )


@router.patch(
    "/Update_profile",
    response_model=FreelancerProfileOut,
    summary="Partially update my freelancer profile - only send the fields you want to change",
)
def update_my_profile(
    payload: FreelancerProfileUpdate,
    current_user: User = Depends(require_freelancer),
    db: Session = Depends(get_db),
):
    profile = profile_service.update_profile(
        db,
        current_user.id,
        payload,
    )
    return _serialize(profile)


@router.delete(
    "/Delete_profile",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete my freelancer profile",
)
def delete_my_profile(
    current_user: User = Depends(require_freelancer),
    db: Session = Depends(get_db),
):
    profile_service.delete_profile(db, current_user.id)