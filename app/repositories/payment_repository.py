import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment import Payment


def get_by_id(
    db: Session,
    payment_id: uuid.UUID,
) -> Payment | None:
    return db.get(Payment, payment_id)


def get_by_milestone(
    db: Session,
    milestone_id: uuid.UUID,
) -> Payment | None:
    return (
        db.execute(
            select(Payment).where(
                Payment.milestone_id == milestone_id
            )
        )
        .scalars()
        .first()
    )


def get_by_checkout_session_id(
    db: Session,
    checkout_session_id: str,
) -> Payment | None:
    return (
        db.execute(
            select(Payment).where(
                Payment.stripe_checkout_session_id
                == checkout_session_id
            )
        )
        .scalars()
        .first()
    )


def create(
    db: Session,
    **fields,
) -> Payment:
    payment = Payment(**fields)

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment


def update(
    db: Session,
    payment: Payment,
    **fields,
) -> Payment:
    for key, value in fields.items():
        if value is not None:
            setattr(payment, key, value)

    db.commit()
    db.refresh(payment)

    return payment


def delete(
    db: Session,
    payment: Payment,
) -> None:
    db.delete(payment)
    db.commit()

    def get_by_stripe_payment_intent_id(
    db: Session,
    payment_intent_id: str,
) -> Payment | None:
     return (
        db.query(Payment)
        .filter(
            Payment.stripe_payment_intent_id
            == payment_intent_id
        )
        .first()
    )