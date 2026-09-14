import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models.enums import ContractStatus
from app.models.user import User
from app.repositories import contract_repository, review_repository
from app.schemas.review import ReviewCreateRequest, ReviewUpdateRequest


def create_review(db: Session, reviewer: User, contract_id: uuid.UUID, data: ReviewCreateRequest):
    contract = contract_repository.get_by_id(db, contract_id)
    if contract is None:
        raise NotFoundError("Contract not found.")

    if reviewer.id == contract.client_id:
        reviewee_id = contract.freelancer_id
    elif reviewer.id == contract.freelancer_id:
        reviewee_id = contract.client_id
    else:
        raise ForbiddenError("You are not a participant of this contract.")

    # A review is allowed only after the related contract is completed.
    if contract.status != ContractStatus.COMPLETED:
        raise ValidationAppError("Reviews can only be submitted for completed contracts.")

    # Each permitted party can submit the review only once per contract.
    if review_repository.get_by_contract_and_reviewer(db, contract_id, reviewer.id):
        raise ConflictError("You have already submitted a review for this contract.")

    return review_repository.create(
        db,
        contract_id=contract_id,
        reviewer_id=reviewer.id,
        reviewee_id=reviewee_id,
        rating=data.rating,
        comment=data.comment,
    )


def get_review_or_404(db: Session, review_id: uuid.UUID):
    review = review_repository.get_by_id(db, review_id)
    if review is None:
        raise NotFoundError("Review not found.")
    return review


def get_review(db: Session, review_id: uuid.UUID):
    return get_review_or_404(db, review_id)


def list_reviews_for_user(db: Session, user_id: uuid.UUID, offset: int, limit: int):
    return review_repository.list_for_reviewee(db, user_id, offset, limit)


def update_review(db: Session, reviewer: User, review_id: uuid.UUID, data: ReviewUpdateRequest):
    review = get_review_or_404(db, review_id)

    if review.reviewer_id != reviewer.id:
        raise ForbiddenError("You can only edit your own review.")

    fields = data.model_dump(exclude_unset=True)
    return review_repository.update(db, review, **fields)


def delete_review(db: Session, reviewer: User, review_id: uuid.UUID) -> None:
    review = get_review_or_404(db, review_id)

    if review.reviewer_id != reviewer.id:
        raise ForbiddenError("You can only delete your own review.")

    review_repository.delete(db, review)