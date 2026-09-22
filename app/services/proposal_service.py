import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models.contract import Contract
from app.models.enums import JobStatus, NotificationEventType, ProposalStatus
from app.models.user import User
from app.repositories import job_repository, proposal_repository
from app.schemas.proposal import ProposalCreateRequest
from app.services import notification_service


def get_proposal_or_404(db: Session, proposal_id: uuid.UUID):
    proposal = proposal_repository.get_by_id(db, proposal_id)
    if proposal is None:
        raise NotFoundError("Proposal not found.")
    return proposal


def submit_proposal(db: Session, freelancer: User, job_id: uuid.UUID, data: ProposalCreateRequest):
    job = job_repository.get_by_id(db, job_id)
    if job is None:
        raise NotFoundError("Job not found.")

    if job.status != JobStatus.PUBLISHED:
        raise ValidationAppError("Proposals can only be submitted to published jobs.")

    if job.client_id == freelancer.id:
        raise ForbiddenError("You cannot submit a proposal to your own job.")

    if proposal_repository.get_by_job_and_freelancer(db, job_id, freelancer.id):
        raise ConflictError("You have already submitted a proposal for this job.")

    proposal = proposal_repository.create(
        db,
        job_id=job_id,
        freelancer_id=freelancer.id,
        cover_letter=data.cover_letter,
        bid_amount=data.bid_amount,
        estimated_duration_days=data.estimated_duration_days,
        status=ProposalStatus.PENDING,
    )

    notification_service.emit(
        NotificationEventType.PROPOSAL_RECEIVED,
        job.client_id,
        {
            "job_title": job.title,
            "freelancer_name": freelancer.full_name or "A freelancer",
            "bid_amount": str(proposal.bid_amount),
        },
        idempotency_key=notification_service.build_idempotency_key(
            NotificationEventType.PROPOSAL_RECEIVED, proposal.id
        ),
    )

    return proposal


def list_proposals_for_job(db: Session, client: User, job_id: uuid.UUID, offset: int, limit: int):
    job = job_repository.get_by_id(db, job_id)
    if job is None:
        raise NotFoundError("Job not found.")
    if job.client_id != client.id:
        raise ForbiddenError("Only the job's owner can view its proposals.")
    return proposal_repository.list_for_job(db, job_id, offset, limit)


def list_my_proposals(db: Session, freelancer: User, offset: int, limit: int):
    return proposal_repository.list_for_freelancer(db, freelancer.id, offset, limit)


def get_proposal_for_participant(db: Session, user: User, proposal_id: uuid.UUID):
    proposal = get_proposal_or_404(db, proposal_id)
    job = job_repository.get_by_id(db, proposal.job_id)
    if job is None:
        raise NotFoundError("Job not found.")
    if user.id not in (proposal.freelancer_id, job.client_id):
        raise ForbiddenError("You are not a participant of this proposal.")
    return proposal


def reject_proposal(db: Session, client: User, proposal_id: uuid.UUID):
    proposal = get_proposal_or_404(db, proposal_id)
    job = job_repository.get_by_id(db, proposal.job_id)
    if job is None:
        raise NotFoundError("Job not found.")

    if job.client_id != client.id:
        raise ForbiddenError("Only the job's owner can reject a proposal for it.")

    if proposal.status != ProposalStatus.PENDING:
        raise ValidationAppError("Only a pending proposal can be rejected.")

    proposal.rejected_at = datetime.now(timezone.utc)

    rejected = proposal_repository.set_status(
        db,
        proposal,
        ProposalStatus.REJECTED,
    )

    notification_service.emit(
        NotificationEventType.PROPOSAL_REJECTED,
        rejected.freelancer_id,
        {"job_title": job.title},
        idempotency_key=notification_service.build_idempotency_key(
            NotificationEventType.PROPOSAL_REJECTED, rejected.id
        ),
    )

    return rejected


def withdraw_proposal(db: Session, freelancer: User, proposal_id: uuid.UUID):
    proposal = get_proposal_or_404(db, proposal_id)

    if proposal.freelancer_id != freelancer.id:
        raise ForbiddenError("You can only withdraw your own proposal.")

    if proposal.status != ProposalStatus.PENDING:
        raise ValidationAppError("Only a pending proposal can be withdrawn.")

    return proposal_repository.set_status(db, proposal, ProposalStatus.WITHDRAWN)


def update_proposal_status(
    db: Session,
    current_user: User,
    proposal_id: uuid.UUID,
    new_status: ProposalStatus,
):
    if new_status == ProposalStatus.REJECTED:
        return reject_proposal(db, current_user, proposal_id)

    if new_status == ProposalStatus.WITHDRAWN:
        return withdraw_proposal(db, current_user, proposal_id)

    raise ValidationAppError(
        "This endpoint only accepts REJECTED or WITHDRAWN. Use /proposals/{proposal_id}/accept to accept."
    )


def delete_proposal(db: Session, freelancer: User, proposal_id: uuid.UUID) -> None:
    proposal = get_proposal_or_404(db, proposal_id)

    if proposal.freelancer_id != freelancer.id:
        raise ForbiddenError("You can only delete your own proposal.")

    if proposal.status != ProposalStatus.PENDING:
        raise ValidationAppError("Only a PENDING proposal can be deleted.")

    proposal_repository.delete(db, proposal)


def accept_proposal(db: Session, client: User, proposal_id: uuid.UUID):
    proposal = get_proposal_or_404(db, proposal_id)
    job = job_repository.get_by_id(db, proposal.job_id)

    if job is None:
        raise NotFoundError("Job not found.")

    if job.client_id != client.id:
        raise ForbiddenError("Only the job's owner can accept a proposal for it.")

    if proposal.status != ProposalStatus.PENDING:
        raise ValidationAppError("Only a pending proposal can be accepted.")

    if job.status == JobStatus.CLOSED or job.contract is not None:
        raise ConflictError("This job is already closed or already has an accepted proposal.")

    now = datetime.now(timezone.utc)

    try:
        proposal.status = ProposalStatus.ACCEPTED
        proposal.accepted_at = now

        proposal_repository.reject_other_pending_for_job(
            db,
            job.id,
            except_proposal_id=proposal.id,
        )

        job.status = JobStatus.CLOSED
        job.closed_at = now

        contract = Contract(
            job_id=job.id,
            proposal_id=proposal.id,
            client_id=client.id,
            freelancer_id=proposal.freelancer_id,
            agreed_amount=proposal.bid_amount,
        )

        db.add(contract)
        db.commit()
        db.refresh(contract)

    except Exception:
        db.rollback()
        raise

    notification_service.emit(
        NotificationEventType.PROPOSAL_ACCEPTED,
        proposal.freelancer_id,
        {"job_title": job.title},
        idempotency_key=notification_service.build_idempotency_key(
            NotificationEventType.PROPOSAL_ACCEPTED, proposal.id
        ),
    )

    for participant_id in (contract.client_id, contract.freelancer_id):
        notification_service.emit(
            NotificationEventType.CONTRACT_CREATED,
            participant_id,
            {"job_title": job.title, "agreed_amount": str(contract.agreed_amount)},
            idempotency_key=notification_service.build_idempotency_key(
                NotificationEventType.CONTRACT_CREATED, contract.id, participant_id
            ),
        )

    return contract