import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError
from app.models.enums import ContractStatus, NotificationEventType
from app.models.user import User
from app.repositories import contract_repository, job_repository, milestone_repository
from app.services import notification_service


def _job_title(db: Session, contract) -> str:
    job = job_repository.get_by_id(db, contract.job_id)
    return job.title if job else "your contract"


def get_contract_or_404(db: Session, contract_id: uuid.UUID):
    contract = contract_repository.get_by_id(db, contract_id)
    if contract is None:
        raise NotFoundError("Contract not found.")
    return contract


def assert_participant(contract, user: User) -> None:
    
    if user.id not in (contract.client_id, contract.freelancer_id):
        raise ForbiddenError("You are not a participant of this contract.")


def get_contract_for_user(db: Session, contract_id: uuid.UUID, user: User):
    contract = get_contract_or_404(db, contract_id)
    assert_participant(contract, user)
    return contract


def list_my_contracts(db: Session, user: User, offset: int, limit: int):
    return contract_repository.list_for_user(db, user.id, offset, limit)


def complete_contract(db: Session, contract_id: uuid.UUID, client: User):
    contract = get_contract_or_404(db, contract_id)

    
    if contract.client_id != client.id:
        raise ForbiddenError("Only the client of this contract can complete it.")

    if contract.status != ContractStatus.ACTIVE:
        raise ValidationAppError("Only an active contract can be completed.")

   
    if not milestone_repository.all_approved(db, contract.id):
        raise ValidationAppError("All milestones must be APPROVED before the contract can be completed.")

    job_title = _job_title(db, contract)
    completed = contract_repository.complete(db, contract)

    for participant_id in (completed.client_id, completed.freelancer_id):
        notification_service.emit(
            NotificationEventType.CONTRACT_COMPLETED,
            participant_id,
            {"job_title": job_title},
            idempotency_key=notification_service.build_idempotency_key(
                NotificationEventType.CONTRACT_COMPLETED, completed.id, participant_id
            ),
        )

    return completed


def cancel_contract(db: Session, contract_id: uuid.UUID, user: User):
    contract = get_contract_or_404(db, contract_id)
    assert_participant(contract, user)

    if contract.status != ContractStatus.ACTIVE:
        raise ValidationAppError("Only an active contract can be cancelled.")

    if milestone_repository.any_approved(db, contract.id):
        raise ValidationAppError(
            "This contract has approved milestones and can no longer be cancelled. Complete it instead."
        )

    job_title = _job_title(db, contract)
    cancelled = contract_repository.cancel(db, contract)

    for participant_id in (cancelled.client_id, cancelled.freelancer_id):
        notification_service.emit(
            NotificationEventType.CONTRACT_CANCELLED,
            participant_id,
            {"job_title": job_title},
            idempotency_key=notification_service.build_idempotency_key(
                NotificationEventType.CONTRACT_CANCELLED, cancelled.id, participant_id
            ),
        )

    return cancelled


def update_contract_status(db: Session, current_user: User, contract_id: uuid.UUID, new_status: ContractStatus):
    if new_status == ContractStatus.COMPLETED:
        return complete_contract(db, contract_id, current_user)
    if new_status == ContractStatus.CANCELLED:
        return cancel_contract(db, contract_id, current_user)
    raise ValidationAppError("This endpoint only accepts COMPLETED or CANCELLED.")


def delete_contract(db: Session, contract_id: uuid.UUID, user: User) -> None:
    contract = get_contract_or_404(db, contract_id)
    assert_participant(contract, user)

    if contract.status != ContractStatus.CANCELLED:
        raise ValidationAppError("Only a CANCELLED contract can be deleted.")

    contract_repository.delete(db, contract)