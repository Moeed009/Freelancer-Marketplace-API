import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ProposalStatus
from app.models.proposal import Proposal


def get_by_id(db: Session, proposal_id: uuid.UUID) -> Proposal | None:
    return db.get(Proposal, proposal_id)


def get_by_job_and_freelancer(
    db: Session,
    job_id: uuid.UUID,
    freelancer_id: uuid.UUID,
) -> Proposal | None:
    return (
        db.query(Proposal)
        .filter(
            Proposal.job_id == job_id,
            Proposal.freelancer_id == freelancer_id,
        )
        .first()
    )


def list_for_job(
    db: Session,
    job_id: uuid.UUID,
    offset: int,
    limit: int,
) -> tuple[list[Proposal], int]:
    query = select(Proposal).where(Proposal.job_id == job_id)

    total = len(
        db.execute(
            select(Proposal.id).where(Proposal.job_id == job_id)
        ).all()
    )

    items = (
        db.execute(
            query.order_by(Proposal.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    return list(items), total


def list_for_freelancer(
    db: Session,
    freelancer_id: uuid.UUID,
    offset: int,
    limit: int,
) -> tuple[list[Proposal], int]:
    query = select(Proposal).where(
        Proposal.freelancer_id == freelancer_id
    )

    total = len(
        db.execute(
            select(Proposal.id).where(
                Proposal.freelancer_id == freelancer_id
            )
        ).all()
    )

    items = (
        db.execute(
            query.order_by(Proposal.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    return list(items), total


def create(db: Session, **fields) -> Proposal:
    proposal = Proposal(**fields)

    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    return proposal


def delete(db: Session, proposal: Proposal) -> None:
    db.delete(proposal)
    db.commit()


def set_status(
    db: Session,
    proposal: Proposal,
    status: ProposalStatus,
) -> Proposal:
    proposal.status = status

    db.commit()
    db.refresh(proposal)

    return proposal


def reject_other_pending_for_job(
    db: Session,
    job_id: uuid.UUID,
    except_proposal_id: uuid.UUID,
) -> None:
    now = datetime.now(timezone.utc)

    (
        db.query(Proposal)
        .filter(
            Proposal.job_id == job_id,
            Proposal.id != except_proposal_id,
            Proposal.status == ProposalStatus.PENDING,
        )
        .update(
            {
                "status": ProposalStatus.REJECTED,
                "rejected_at": now,
            },
            synchronize_session=False,
        )
    )