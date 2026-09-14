import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.skill import SkillCreate, SkillUpdate, SkillOut
from app.services import skill_service


router = APIRouter(
    prefix="",
    tags=["Skills"]
)


@router.get(
    "/List All skills",
    response_model=list[SkillOut],
    summary="List all reusable skills",
)
def list_skills(
    db: Session = Depends(get_db),
):
    return skill_service.list_skills(db)


@router.post(
    "/Create_Skill",
    response_model=SkillOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a reusable skill tag (any authenticated user - there is no admin role in this project)",
)
def create_skill(
    payload: SkillCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return skill_service.create_skill(
        db,
        payload.name
    )


@router.patch(
    "/Update_skill",
    response_model=SkillOut,
    summary="Update a reusable skill tag",
)
def update_skill(
    skill_id: uuid.UUID,
    payload: SkillUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return skill_service.update_skill(
        db,
        skill_id,
        payload
    )


@router.delete(
    "/Delete_Skill",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a reusable skill tag",
)
def delete_skill(
    skill_id: uuid.UUID,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    skill_service.delete_skill(
        db,
        skill_id
    )