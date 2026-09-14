import math
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user, require_client, require_freelancer
from app.dependencies.pagination import PaginationParams
from app.models.user import User
from app.schemas.common import Page
from app.schemas.contract import ContractOut
from app.schemas.proposal import ProposalCreateRequest, ProposalOut, ProposalStatusUpdateRequest
from app.services import proposal_service

router = APIRouter(tags=["Proposals"])


@router.post(
    "/Submit_proposal",
    response_model=ProposalOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a proposal for a job (FREELANCER only)",
)
def submit_proposal(
    job_id: uuid.UUID,
    payload: ProposalCreateRequest,
    freelancer: User = Depends(require_freelancer),
    db: Session = Depends(get_db),
):
    return proposal_service.submit_proposal(db, freelancer, job_id, payload)


@router.get(
    "/received_proposals",
    response_model=Page[ProposalOut],
    summary="List proposals received for a job you own (CLIENT only)",
)
def list_proposals_for_job(
    job_id: uuid.UUID,
    client: User = Depends(require_client),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    items, total = proposal_service.list_proposals_for_job(db, client, job_id, pagination.offset, pagination.page_size)
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=math.ceil(total / pagination.page_size) if total else 0,
    )


@router.get(
    "/List_proposals",
    response_model=Page[ProposalOut],
    summary="List my own submitted proposals (FREELANCER only)",
)
def list_my_proposals(
    freelancer: User = Depends(require_freelancer),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    items, total = proposal_service.list_my_proposals(db, freelancer, pagination.offset, pagination.page_size)
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=math.ceil(total / pagination.page_size) if total else 0,
    )



@router.post(
    "/Accept_proposal",
    response_model=ContractOut,
    summary="Accept a proposal (CLIENT only) - creates a contract and closes the job",
)
def accept_proposal(proposal_id: uuid.UUID, client: User = Depends(require_client), db: Session = Depends(get_db)):
    return proposal_service.accept_proposal(db, client, proposal_id)


@router.patch(
    "/Status_Update",
    response_model=ProposalOut,
    summary="Reject (CLIENT, own job) or withdraw (FREELANCER, own proposal) a pending proposal",
)
def update_proposal_status(
    proposal_id: uuid.UUID,
    payload: ProposalStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return proposal_service.update_proposal_status(db, current_user, proposal_id, payload.status)


@router.delete(
    "/Delete_proposal",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete your own proposal, only while it is PENDING (FREELANCER only)",
)
def delete_proposal(
    proposal_id: uuid.UUID,
    freelancer: User = Depends(require_freelancer),
    db: Session = Depends(get_db),
):
    proposal_service.delete_proposal(db, freelancer, proposal_id)