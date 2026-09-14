import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.enums import ContractStatus


def get_by_id(db: Session, contract_id: uuid.UUID) -> Contract | None:
    return db.get(Contract, contract_id)


def list_for_user(db: Session, user_id: uuid.UUID, offset: int, limit: int) -> tuple[list[Contract], int]:
    base = select(Contract).where((Contract.client_id == user_id) | (Contract.freelancer_id == user_id))
    total = len(db.execute(select(Contract.id).where(
        (Contract.client_id == user_id) | (Contract.freelancer_id == user_id)
    )).all())
    items = db.execute(base.order_by(Contract.created_at.desc()).offset(offset).limit(limit)).scalars().all()
    return list(items), total


def create(db: Session, **fields) -> Contract:
    contract = Contract(**fields)
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


def complete(db: Session, contract: Contract) -> Contract:
    contract.status = ContractStatus.COMPLETED
    contract.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(contract)
    return contract


def cancel(db: Session, contract: Contract) -> Contract:
    contract.status = ContractStatus.CANCELLED
    db.commit()
    db.refresh(contract)
    return contract


def delete(db: Session, contract: Contract) -> None:
    db.delete(contract)
    db.commit()