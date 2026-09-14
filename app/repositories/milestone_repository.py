import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import MilestoneStatus
from app.models.milestone import Milestone


def get_by_id(db: Session, milestone_id: uuid.UUID) -> Milestone | None:
    return db.get(Milestone, milestone_id)


def list_for_contract(db: Session, contract_id: uuid.UUID) -> list[Milestone]:
    return (
        db.execute(select(Milestone).where(Milestone.contract_id == contract_id).order_by(Milestone.created_at))
        .scalars()
        .all()
    )


def create(db: Session, **fields) -> Milestone:
    milestone = Milestone(**fields)
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


def update(db: Session, milestone: Milestone, **fields) -> Milestone:
    for key, value in fields.items():
        if value is not None:
            setattr(milestone, key, value)
    db.commit()
    db.refresh(milestone)
    return milestone


def delete(db: Session, milestone: Milestone) -> None:
    db.delete(milestone)
    db.commit()


def set_status(db: Session, milestone: Milestone, status: MilestoneStatus) -> Milestone:
    milestone.status = status
    db.commit()
    db.refresh(milestone)
    return milestone


def all_approved(db: Session, contract_id: uuid.UUID) -> bool:
    milestones = list_for_contract(db, contract_id)
    if not milestones:
        return False
    return all(m.status == MilestoneStatus.APPROVED for m in milestones)


def any_approved(db: Session, contract_id: uuid.UUID) -> bool:
    milestones = list_for_contract(db, contract_id)
    return any(m.status == MilestoneStatus.APPROVED for m in milestones)


def set_deliverable_url(db: Session, milestone: Milestone, deliverable_url: str) -> Milestone:
    milestone.deliverable_url = deliverable_url
    db.commit()
    db.refresh(milestone)
    return milestone