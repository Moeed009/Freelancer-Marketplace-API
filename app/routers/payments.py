import stripe
from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import require_client
from app.models.user import User
from app.schemas.payment import CheckoutResponse, PaymentCreate
from app.services import payment_service
from app.services import stripe_service


router = APIRouter(
    tags=["Payments"],
)


@router.post(
    "/payments/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary=(
        "Create a Stripe Checkout session "
        "for a milestone (CLIENT only)"
    ),
)
def create_checkout(
    payload: PaymentCreate,
    client: User = Depends(require_client),
    db: Session = Depends(get_db),
):
    try:
        payment, checkout_url = (
            payment_service.create_checkout_for_milestone(
                db,
                milestone_id=payload.milestone_id,
                client=client,
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return CheckoutResponse(
        payment_id=payment.id,
        checkout_url=checkout_url,
        status=payment.status,
    )


@router.post(
    "/payments/webhook",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(
        default=None,
        alias="Stripe-Signature",
    ),
    db: Session = Depends(get_db),
):
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    payload = await request.body()

    try:
        event = stripe_service.construct_webhook_event(
            payload,
            stripe_signature,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook signature",
        ) from exc

    if event["type"] in {
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
}:
     payment_service.handle_checkout_completed(
        db,
        event["data"]["object"],
    )

    elif event["type"] == "payment_intent.succeeded":
     payment_service.handle_payment_intent_succeeded(
        db,
        event["data"]["object"],
    )

    elif event["type"] == "payment_intent.processing":
     payment_service.handle_payment_intent_processing(
        db,
        event["data"]["object"],
    )

    elif event["type"] == "payment_intent.payment_failed":
     payment_service.handle_payment_intent_failed(
        db,
        event["data"]["object"],
    )

    elif event["type"] == "payment_intent.canceled":
     payment_service.handle_payment_intent_canceled(
        db,
        event["data"]["object"],
    )