import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError
from app.models.enums import ContractStatus, MilestoneStatus
from app.models.user import User
from app.repositories import contract_repository, milestone_repository
from app.schemas.milestone import MilestoneCreateRequest, MilestoneUpdateRequest
from app.core.supabase_storage import upload_deliverable

ALLOWED_DELIVERABLE_TYPES = {
    "image/jpeg", "image/png", "image/webp",
    "application/pdf", "application/zip",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_DELIVERABLE_SIZE = 20 * 1024 * 1024  # 20 MB

_TRANSITIONS: dict[tuple[str, MilestoneStatus], set[MilestoneStatus]] = {
    ("FREELANCER", MilestoneStatus.SUBMITTED): {MilestoneStatus.PENDING, MilestoneStatus.REJECTED},
    ("CLIENT", MilestoneStatus.APPROVED): {MilestoneStatus.SUBMITTED},
    ("CLIENT", MilestoneStatus.REJECTED): {MilestoneStatus.SUBMITTED},
}


def _get_contract_and_check_active(db: Session, contract_id: uuid.UUID):
    contract = contract_repository.get_by_id(db, contract_id)
    if contract is None:
        raise NotFoundError("Contract not found.")
    return contract


def create_milestone(db: Session, client: User, contract_id: uuid.UUID, data: MilestoneCreateRequest):
    contract = _get_contract_and_check_active(db, contract_id)
    if contract.client_id != client.id:
        raise ForbiddenError("Only the contract's client can create milestones.")
    if contract.status != ContractStatus.ACTIVE:
        raise ValidationAppError("Milestones can only be added to an active contract.")

    return milestone_repository.create(
        db,
        contract_id=contract.id,
        title=data.title,
        description=data.description,
        amount=data.amount,
        due_date=data.due_date,
        status=MilestoneStatus.PENDING,
    )


def list_milestones(db: Session, user: User, contract_id: uuid.UUID):
    contract = _get_contract_and_check_active(db, contract_id)
    if user.id not in (contract.client_id, contract.freelancer_id):
        raise ForbiddenError("You are not a participant of this contract.")
    return milestone_repository.list_for_contract(db, contract.id)


def update_milestone_status(db: Session, user: User, milestone_id: uuid.UUID, new_status: MilestoneStatus):
    milestone = milestone_repository.get_by_id(db, milestone_id)
    if milestone is None:
        raise NotFoundError("Milestone not found.")

    contract = _get_contract_and_check_active(db, milestone.contract_id)

    if user.id == contract.freelancer_id:
        role = "FREELANCER"
    elif user.id == contract.client_id:
        role = "CLIENT"
    else:
        raise ForbiddenError("You are not a participant of this contract.")

    allowed_prior = _TRANSITIONS.get((role, new_status))
    if allowed_prior is None or milestone.status not in allowed_prior:
        raise ValidationAppError(
            f"Invalid milestone transition: {role} cannot move status from {milestone.status.value} to {new_status.value}."
        )

    return milestone_repository.set_status(db, milestone, new_status)


def _get_milestone_owned_by_client(db: Session, client: User, milestone_id: uuid.UUID):
    milestone = milestone_repository.get_by_id(db, milestone_id)
    if milestone is None:
        raise NotFoundError("Milestone not found.")

    contract = _get_contract_and_check_active(db, milestone.contract_id)
    if contract.client_id != client.id:
        raise ForbiddenError("Only the contract's client can modify this milestone.")

    return milestone


def update_milestone(db: Session, client: User, milestone_id: uuid.UUID, data: MilestoneUpdateRequest):
    milestone = _get_milestone_owned_by_client(db, client, milestone_id)

    if milestone.status != MilestoneStatus.PENDING:
        raise ValidationAppError("Only a PENDING milestone (no work submitted yet) can be edited.")

    fields = data.model_dump(exclude_unset=True)
    return milestone_repository.update(db, milestone, **fields)


def delete_milestone(db: Session, client: User, milestone_id: uuid.UUID) -> None:
    milestone = _get_milestone_owned_by_client(db, client, milestone_id)

    if milestone.status != MilestoneStatus.PENDING:
        raise ValidationAppError("Only a PENDING milestone (no work submitted yet) can be deleted.")

    milestone_repository.delete(db, milestone)


async def submit_deliverable(
    db: Session, freelancer: User, milestone_id: uuid.UUID, file_bytes: bytes, content_type: str
):
    if content_type not in ALLOWED_DELIVERABLE_TYPES:
        raise ValidationAppError("Unsupported file type for a deliverable.")
    if len(file_bytes) > MAX_DELIVERABLE_SIZE:
        raise ValidationAppError("File size must not exceed 20MB.")

    milestone = milestone_repository.get_by_id(db, milestone_id)
    if milestone is None:
        raise NotFoundError("Milestone not found.")

    contract = _get_contract_and_check_active(db, milestone.contract_id)
    if contract.freelancer_id != freelancer.id:
        raise ForbiddenError("Only the contract's freelancer can submit a deliverable.")

    if milestone.status not in (MilestoneStatus.PENDING, MilestoneStatus.REJECTED):
        raise ValidationAppError(
            f"Cannot submit a deliverable while milestone is {milestone.status.value}."
        )

    deliverable_url = await upload_deliverable(file_bytes, content_type, milestone.id)
    milestone_repository.set_deliverable_url(db, milestone, deliverable_url)
    return milestone_repository.set_status(db, milestone, MilestoneStatus.SUBMITTED)