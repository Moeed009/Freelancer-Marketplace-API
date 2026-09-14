import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user, require_client, require_freelancer
from app.models.user import User
from app.schemas.milestone import (
    MilestoneCreateRequest,
    MilestoneOut,
    MilestoneStatusUpdateRequest,
    MilestoneUpdateRequest,
)
from app.services import milestone_service

router = APIRouter(tags=["Milestones"])


@router.post(
    "/Add a milestone",
    response_model=MilestoneOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a milestone to a contract (CLIENT only)",
)
def create_milestone(
    contract_id: uuid.UUID,
    payload: MilestoneCreateRequest,
    client: User = Depends(require_client),
    db: Session = Depends(get_db),
):
    return milestone_service.create_milestone(db, client, contract_id, payload)


@router.get(
    "/List milestones",
    response_model=list[MilestoneOut],
    summary="List milestones for a contract you participate in",
)
def list_milestones(contract_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return milestone_service.list_milestones(db, current_user, contract_id)


@router.patch(
    "/Update a milestone",
    response_model=MilestoneOut,
    summary="Edit a milestone's details (title/description/amount/due_date) - CLIENT only, while PENDING",
)
def update_milestone(
    milestone_id: uuid.UUID,
    payload: MilestoneUpdateRequest,
    client: User = Depends(require_client),
    db: Session = Depends(get_db),
):
    return milestone_service.update_milestone(db, client, milestone_id, payload)


@router.patch(
    "/Milestone Status",
    response_model=MilestoneOut,
    summary=(
        "Transition a milestone's status only (freelancer submits; client approves/rejects), "
        "without touching its other fields"
    ),
)
def update_milestone_status(
    milestone_id: uuid.UUID,
    payload: MilestoneStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return milestone_service.update_milestone_status(db, current_user, milestone_id, payload.status)


@router.delete(
    "/Delete a milestone",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a milestone, only while it is PENDING (CLIENT only)",
)
def delete_milestone(milestone_id: uuid.UUID, client: User = Depends(require_client), db: Session = Depends(get_db)):
    milestone_service.delete_milestone(db, client, milestone_id)


@router.post(
    "/Submit a deliverable file",
    response_model=MilestoneOut,
    summary="Submit a deliverable file for a milestone (FREELANCER only, moves status to SUBMITTED)",
)
async def submit_milestone_deliverable(
    milestone_id: uuid.UUID,
    file: UploadFile = File(...),
    freelancer: User = Depends(require_freelancer),
    db: Session = Depends(get_db),
):
    file_bytes = await file.read()
    return await milestone_service.submit_deliverable(db, freelancer, milestone_id, file_bytes, file.content_type)