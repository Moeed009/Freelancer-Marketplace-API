import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import PaymentStatus
from app.models.payment import Payment
from app.models.user import User
from app.repositories import milestone_repository
from app.repositories import payment_repository
from app.services import stripe_service


def create_checkout_for_milestone(
    db: Session,
    *,
    milestone_id: uuid.UUID,
    client: User,
) -> tuple[Payment, str]:
    milestone = milestone_repository.get_by_id(
        db,
        milestone_id,
    )

    if not milestone:
        raise ValueError("Milestone not found")

    contract = milestone.contract

    if contract.client_id != client.id:
        raise ValueError(
            "You are not authorized to pay this milestone"
        )

    existing_payment = payment_repository.get_by_milestone(
        db,
        milestone.id,
    )

    if existing_payment:
        raise ValueError(
            "Payment already exists for this milestone"
        )

    amount = Decimal(str(milestone.amount))
    amount_in_cents = int(amount * 100)

    payment = payment_repository.create(
        db,
        milestone_id=milestone.id,
        client_id=contract.client_id,
        freelancer_id=contract.freelancer_id,
        amount=amount,
        currency="USD",
        status=PaymentStatus.PENDING,
    )

    try:
        session = stripe_service.create_checkout_session(
            amount=amount_in_cents,
            currency="USD",
            success_url=(
                "http://localhost:8000/payment/success"
            ),
            cancel_url=(
                "http://localhost:8000/payment/cancel"
            ),
            metadata={
                "payment_id": str(payment.id),
                "milestone_id": str(milestone.id),
                "client_id": str(client.id),
            },
        )
    except Exception:
        payment_repository.delete(
            db,
            payment,
        )
        raise

    payment = payment_repository.update(
        db,
        payment,
        stripe_checkout_session_id=session.id,
    )

    return payment, session.url


def handle_checkout_completed(
    db: Session,
    checkout_session,
) -> Payment | None:
    metadata = checkout_session.get("metadata") or {}

    payment_id = metadata.get("payment_id")

    if not payment_id:
        return None

    try:
        payment_uuid = uuid.UUID(payment_id)
    except ValueError:
        return None

    payment = payment_repository.get_by_id(
        db,
        payment_uuid,
    )

    if not payment:
        return None

    if payment.status == PaymentStatus.PAID:
        return payment

    payment_status = checkout_session.get(
        "payment_status"
    )

    if payment_status != "paid":
        return payment

    payment_intent_id = checkout_session.get(
        "payment_intent"
    )

    return payment_repository.update(
        db,
        payment,
        status=PaymentStatus.PAID,
        stripe_payment_intent_id=payment_intent_id,
    )

def handle_payment_intent_succeeded(
    db: Session,
    payment_intent,
) -> Payment | None:
    payment_intent_id = payment_intent.get("id")

    if not payment_intent_id:
        return None

    payment = payment_repository.get_by_stripe_payment_intent_id(
        db,
        payment_intent_id,
    )

    if not payment:
        return None

    return payment_repository.update(
        db,
        payment,
        status=PaymentStatus.PAID,
        stripe_payment_intent_id=payment_intent_id,
    )

def handle_payment_intent_failed(
    db: Session,
    payment_intent,
) -> Payment | None:
    payment_intent_id = payment_intent.get("id")

    if not payment_intent_id:
        return None

    payment = payment_repository.get_by_stripe_payment_intent_id(
        db,
        payment_intent_id,
    )

    if not payment:
        return None

    last_payment_error = (
        payment_intent.get("last_payment_error") or {}
    )

    return payment_repository.update(
        db,
        payment,
        status=PaymentStatus.FAILED,
        stripe_payment_intent_id=payment_intent_id,
        stripe_payment_error_code=last_payment_error.get(
            "code"
        ),
        stripe_payment_error_message=last_payment_error.get(
            "message"
        ),
    )
def handle_payment_intent_processing(
    db: Session,
    payment_intent,
) -> Payment | None:
    payment_intent_id = payment_intent.get("id")

    if not payment_intent_id:
        return None

    payment = payment_repository.get_by_stripe_payment_intent_id(
        db,
        payment_intent_id,
    )

    if not payment:
        return None

    return payment_repository.update(
        db,
        payment,
        status=PaymentStatus.PROCESSING,
    )

def handle_payment_intent_canceled(
    db: Session,
    payment_intent,
) -> Payment | None:
    payment_intent_id = payment_intent.get("id")

    if not payment_intent_id:
        return None

    payment = payment_repository.get_by_stripe_payment_intent_id(
        db,
        payment_intent_id,
    )

    if not payment:
        return None

    return payment_repository.update(
        db,
        payment,
        status=PaymentStatus.CANCELLED,
    )
def cancel_payment(
    db: Session,
    payment: Payment,
):
    if payment.status in {
        PaymentStatus.PAID,
        PaymentStatus.REFUNDED,
    }:
        raise ValueError(
            "Paid payment cannot be cancelled. Use refund."
        )

    if not payment.stripe_payment_intent_id:
        raise ValueError(
            "Stripe PaymentIntent not found"
        )

    payment_intent = stripe_service.cancel_payment_intent(
        payment.stripe_payment_intent_id,
    )

    return payment_intent