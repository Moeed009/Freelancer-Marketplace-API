import stripe

from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(
    *,
    amount: int,
    currency: str,
    success_url: str,
    cancel_url: str,
    metadata: dict[str, str],
):
    return stripe.checkout.Session.create(
        mode="payment",
        managed_payments={"enabled": False},
        line_items=[
            {
                "price_data": {
                    "currency": currency.lower(),
                    "product_data": {
                        "name": "Freelancer Marketplace Milestone",
                    },
                    "unit_amount": amount,
                },
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
    )


def construct_webhook_event(
    payload: bytes,
    signature: str,
):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise ValueError(
            "STRIPE_WEBHOOK_SECRET is not configured"
        )

    return stripe.Webhook.construct_event(
        payload,
        signature,
        settings.STRIPE_WEBHOOK_SECRET,
    )