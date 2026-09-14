import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review import Review


def get_by_id(db: Session, review_id: uuid.UUID) -> Review | None:
    return db.get(Review, review_id)


def get_by_contract_and_reviewer(db: Session, contract_id: uuid.UUID, reviewer_id: uuid.UUID) -> Review | None:
    return (
        db.query(Review)
        .filter(Review.contract_id == contract_id, Review.reviewer_id == reviewer_id)
        .first()
    )


def list_for_reviewee(db: Session, reviewee_id: uuid.UUID, offset: int, limit: int) -> tuple[list[Review], int]:
    base = select(Review).where(Review.reviewee_id == reviewee_id)
    total = len(db.execute(select(Review.id).where(Review.reviewee_id == reviewee_id)).all())
    items = db.execute(base.order_by(Review.created_at.desc()).offset(offset).limit(limit)).scalars().all()
    return list(items), total


def create(db: Session, **fields) -> Review:
    review = Review(**fields)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def update(db: Session, review: Review, **fields) -> Review:
    for key, value in fields.items():
        if value is not None:
            setattr(review, key, value)
    db.commit()
    db.refresh(review)
    return review


def delete(db: Session, review: Review) -> None:
    db.delete(review)
    db.commit()