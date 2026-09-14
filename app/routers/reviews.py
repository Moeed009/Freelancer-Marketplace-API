import math
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import PaginationParams
from app.models.user import User
from app.schemas.common import Page
from app.schemas.review import ReviewCreateRequest, ReviewOut, ReviewUpdateRequest
from app.services import review_service

router = APIRouter(tags=["Reviews"])


@router.post(
    "/Post_Reviews",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
    summary="Review the other participant of a completed contract (client reviews freelancer, or freelancer reviews client)",
)
def create_review(
    contract_id: uuid.UUID,
    payload: ReviewCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return review_service.create_review(db, current_user, contract_id, payload)



@router.get("/List_reviews", response_model=Page[ReviewOut], summary="List reviews received by a user")
def list_reviews_for_user(user_id: uuid.UUID, pagination: PaginationParams = Depends(), db: Session = Depends(get_db)):
    items, total = review_service.list_reviews_for_user(db, user_id, pagination.offset, pagination.page_size)
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=math.ceil(total / pagination.page_size) if total else 0,
    )


@router.patch(
    "/Update_review",
    response_model=ReviewOut,
    summary="Edit your own review's rating/comment (reviewer only)",
)
def update_review(
    review_id: uuid.UUID,
    payload: ReviewUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return review_service.update_review(db, current_user, review_id, payload)


@router.delete(
    "/Delete_review",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete your own review (reviewer only)",
)
def delete_review(review_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    review_service.delete_review(db, current_user, review_id)