import math
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import PaginationParams
from app.models.user import User
from app.schemas.common import Page
from app.schemas.contract import ContractOut, ContractStatusUpdateRequest
from app.services import contract_service

router = APIRouter(prefix="", tags=["Contracts"])


@router.get("/List_contracts", response_model=Page[ContractOut], summary="List contracts I'm a participant of")
def list_my_contracts(
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    items, total = contract_service.list_my_contracts(db, current_user, pagination.offset, pagination.page_size)
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=math.ceil(total / pagination.page_size) if total else 0,
    )



@router.patch(
    "/Contract_Status",
    response_model=ContractOut,
    summary=(
        "Complete (CLIENT only, all milestones APPROVED) or cancel (either participant, "
        "blocked once any milestone is APPROVED) a contract"
    ),
)
def update_contract_status(
    contract_id: uuid.UUID,
    payload: ContractStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return contract_service.update_contract_status(db, current_user, contract_id, payload.status)


@router.delete(
    "/delete_contract",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a contract, only while it is CANCELLED (either participant)",
)
def delete_contract(contract_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contract_service.delete_contract(db, contract_id, current_user)