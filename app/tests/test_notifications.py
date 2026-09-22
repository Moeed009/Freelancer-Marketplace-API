

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.enums import (
    DeliveryStatus,
    JobStatus,
    NotificationCategory,
    NotificationChannel,
    NotificationEventType,
    ProposalStatus,
    RateType,
)
from app.models.job import Job
from app.models.notification import NotificationDelivery, NotificationEvent, NotificationPreference
from app.models.proposal import Proposal
from app.notifications import providers, templates
from app.schemas.job import JobCreateRequest
from app.services import job_service, notification_dispatcher, notification_service




def _make_job(db, client_user, title="Build an API"):
    job = Job(
        client_id=client_user.id,
        title=title,
        description="Some description",
        rate_type=RateType.FIXED,
        budget_min=100,
        budget_max=500,
        status=JobStatus.PUBLISHED,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _make_draft_job(db, client_user, title="Build an API"):
    job = Job(
        client_id=client_user.id,
        title=title,
        description="Some description",
        rate_type=RateType.FIXED,
        budget_min=100,
        budget_max=500,
        status=JobStatus.DRAFT,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _deliveries(db, event_id) -> list[NotificationDelivery]:
    return list(
        db.execute(
            select(NotificationDelivery).where(NotificationDelivery.event_id == event_id)
        ).scalars().all()
    )


def _emit_simple(user, key_suffix="1"):
    return notification_service.emit(
        NotificationEventType.PROPOSAL_REJECTED,
        user.id,
        {"job_title": "Build an API"},
        idempotency_key=f"PROPOSAL_REJECTED:{key_suffix}",
    )





def test_template_renders_with_payload_variables():
    message = templates.render(
        NotificationEventType.PROPOSAL_RECEIVED,
        NotificationChannel.EMAIL,
        {"job_title": "Build an API", "freelancer_name": "Ali", "bid_amount": "300"},
        app_name="Marketplace",
    )

    assert "Build an API" in message.subject
    assert "Ali" in message.body
    assert "300" in message.body
    assert "$" not in message.body.replace("$app_name", "")  # no unsubstituted placeholders


def test_template_raises_on_missing_variable():
    with pytest.raises(templates.TemplateRenderError):
        templates.render(
            NotificationEventType.PROPOSAL_RECEIVED,
            NotificationChannel.EMAIL,
            {"job_title": "Build an API"},  # freelancer_name/bid_amount missing
            app_name="Marketplace",
        )


def test_every_delivery_is_on_the_email_channel(db, freelancer_user):
    # Email-only project: no event should ever produce a non-EMAIL delivery.
    event_id = _emit_simple(freelancer_user)

    channels = {delivery.channel for delivery in _deliveries(db, event_id)}
    assert channels == {NotificationChannel.EMAIL}




def test_emit_creates_event_and_pending_delivery(db, freelancer_user):
    event_id = _emit_simple(freelancer_user)

    event = db.get(NotificationEvent, event_id)
    assert event.recipient_id == freelancer_user.id
    assert event.category == NotificationCategory.PROPOSAL

    deliveries = _deliveries(db, event_id)
    assert len(deliveries) == 1
    assert deliveries[0].status == DeliveryStatus.PENDING
    assert deliveries[0].attempt_count == 0


def test_emit_is_idempotent_for_the_same_business_event(db, freelancer_user):
    first = _emit_simple(freelancer_user)
    second = _emit_simple(freelancer_user)  # same idempotency key

    assert first == second

    total_events = db.execute(select(NotificationEvent)).scalars().all()
    assert len(total_events) == 1
    assert len(_deliveries(db, first)) == 1


def test_emit_stores_masked_destination_not_the_real_address(db, freelancer_user):
    event_id = _emit_simple(freelancer_user)
    delivery = _deliveries(db, event_id)[0]

    assert delivery.destination_masked != freelancer_user.email
    assert "***" in delivery.destination_masked


def test_emit_with_missing_required_payload_field_records_nothing(db, freelancer_user):
    event_id = notification_service.emit(
        NotificationEventType.PROPOSAL_RECEIVED,
        freelancer_user.id,
        {"job_title": "Build an API"},  # missing freelancer_name / bid_amount
        idempotency_key="PROPOSAL_RECEIVED:bad",
    )

    
    assert event_id is None
    assert db.execute(select(NotificationEvent)).scalars().all() == []


def test_emit_for_unknown_recipient_does_not_raise(db):
    event_id = notification_service.emit(
        NotificationEventType.PROPOSAL_REJECTED,
        uuid.uuid4(),
        {"job_title": "Ghost job"},
        idempotency_key="PROPOSAL_REJECTED:ghost",
    )
    assert event_id is None





def test_dispatcher_sends_pending_delivery(db, freelancer_user, email_provider):
    event_id = _emit_simple(freelancer_user)

    processed = notification_dispatcher.process_due_deliveries()

    assert processed == 1
    assert len(email_provider.sent) == 1
    destination, _ = email_provider.sent[0]
    assert destination == freelancer_user.email

    db.expire_all()
    delivery = _deliveries(db, event_id)[0]
    assert delivery.status == DeliveryStatus.SENT
    assert delivery.sent_at is not None
    assert delivery.attempt_count == 1


def test_transient_failure_is_retried_and_then_succeeds(db, freelancer_user, email_provider):
    email_provider.script = [providers.TransientProviderError("502 upstream")]
    event_id = _emit_simple(freelancer_user)

    # First tick fails transiently.
    notification_dispatcher.process_due_deliveries()
    db.expire_all()
    delivery = _deliveries(db, event_id)[0]

    assert delivery.status == DeliveryStatus.PENDING  # still queued
    assert delivery.attempt_count == 1
    assert delivery.next_attempt_at is not None
    assert "Transient" in delivery.last_error

    # Nothing is due yet - backoff must actually hold the row back.
    assert notification_dispatcher.process_due_deliveries() == 0

    # Second tick, after the backoff window, succeeds.
    later = datetime.now(timezone.utc) + timedelta(hours=1)
    notification_dispatcher.process_due_deliveries(now=later)

    db.expire_all()
    delivery = _deliveries(db, event_id)[0]
    assert delivery.status == DeliveryStatus.SENT
    assert delivery.attempt_count == 2
    assert delivery.last_error is None


def test_permanent_failure_is_not_retried(db, freelancer_user, email_provider):
    email_provider.script = [providers.PermanentProviderError("400 invalid address")]
    event_id = _emit_simple(freelancer_user)

    notification_dispatcher.process_due_deliveries()

    db.expire_all()
    delivery = _deliveries(db, event_id)[0]
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.attempt_count == 1
    assert delivery.next_attempt_at is None

    # Never picked up again, no matter how far in the future.
    later = datetime.now(timezone.utc) + timedelta(days=7)
    assert notification_dispatcher.process_due_deliveries(now=later) == 0
    assert email_provider.calls == 1


def test_retries_are_bounded_by_max_attempts(db, freelancer_user, email_provider):
    email_provider.script = [providers.TransientProviderError("502")] * 10
    event_id = _emit_simple(freelancer_user)

    now = datetime.now(timezone.utc)
    for _ in range(settings.NOTIFICATION_MAX_ATTEMPTS + 2):
        now += timedelta(hours=1)
        notification_dispatcher.process_due_deliveries(now=now)

    db.expire_all()
    delivery = _deliveries(db, event_id)[0]
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.attempt_count == settings.NOTIFICATION_MAX_ATTEMPTS
    assert "Retries exhausted" in delivery.last_error


def test_unexpected_provider_exception_does_not_kill_the_batch(db, freelancer_user, email_provider):
    email_provider.script = [RuntimeError("provider library blew up")]
    event_id = _emit_simple(freelancer_user)

    # Must not propagate out of the dispatcher.
    assert notification_dispatcher.process_due_deliveries() == 1

    db.expire_all()
    delivery = _deliveries(db, event_id)[0]
    assert delivery.status == DeliveryStatus.PENDING  # treated as retryable
    assert "Unexpected" in delivery.last_error




def test_disabled_preference_skips_the_channel(db, freelancer_user, email_provider):
    db.add(
        NotificationPreference(
            user_id=freelancer_user.id,
            category=NotificationCategory.PROPOSAL,
            channel=NotificationChannel.EMAIL,
            enabled=False,
        )
    )
    db.commit()

    event_id = _emit_simple(freelancer_user)

    delivery = _deliveries(db, event_id)[0]
    assert delivery.status == DeliveryStatus.SKIPPED
    assert delivery.last_error == "disabled_by_preference"

    # The dispatcher never touches SKIPPED rows.
    assert notification_dispatcher.process_due_deliveries() == 0
    assert email_provider.sent == []


def test_mandatory_category_ignores_a_disabled_preference(db, client_user, email_provider):
    db.add(
        NotificationPreference(
            user_id=client_user.id,
            category=NotificationCategory.CONTRACT,
            channel=NotificationChannel.EMAIL,
            enabled=False,
        )
    )
    db.commit()

    event_id = notification_service.emit(
        NotificationEventType.CONTRACT_CREATED,
        client_user.id,
        {"job_title": "Build an API", "agreed_amount": "300"},
        idempotency_key="CONTRACT_CREATED:mandatory",
    )

    statuses = {delivery.status for delivery in _deliveries(db, event_id)}
    assert DeliveryStatus.PENDING in statuses  # sent anyway




def test_submitting_a_proposal_notifies_the_job_owner(db, client_user, freelancer_user, as_user):
    job = _make_job(db, client_user)

    response = as_user(freelancer_user).post(
        f"/Submit_proposal?job_id={job.id}",
        json={"cover_letter": "I can do this", "bid_amount": 300, "estimated_duration_days": 7},
    )
    assert response.status_code == 201

    events = db.execute(
        select(NotificationEvent).where(
            NotificationEvent.event_type == NotificationEventType.PROPOSAL_RECEIVED.value
        )
    ).scalars().all()

    assert len(events) == 1
    assert events[0].recipient_id == client_user.id  # the client, not the freelancer


def test_provider_outage_does_not_break_the_business_transaction(
    db, client_user, freelancer_user, as_user, email_provider
):
    email_provider.script = [providers.TransientProviderError("provider down")] * 5
    job = _make_job(db, client_user)

    response = as_user(freelancer_user).post(
        f"/Submit_proposal?job_id={job.id}",
        json={"cover_letter": "I can do this", "bid_amount": 300, "estimated_duration_days": 7},
    )

    
    assert response.status_code == 201
    proposals = db.execute(select(Proposal)).scalars().all()
    assert len(proposals) == 1
    assert proposals[0].status == ProposalStatus.PENDING


def test_retrying_the_same_business_action_does_not_duplicate_notifications(
    db, client_user, freelancer_user, as_user
):
    job = _make_job(db, client_user)
    client = as_user(freelancer_user)
    payload = {"cover_letter": "I can do this", "bid_amount": 300, "estimated_duration_days": 7}

    assert client.post(f"/Submit_proposal?job_id={job.id}", json=payload).status_code == 201
    
    assert client.post(f"/Submit_proposal?job_id={job.id}", json=payload).status_code == 409

    # ...and crucially, only one notification exists.
    events = db.execute(
        select(NotificationEvent).where(
            NotificationEvent.event_type == NotificationEventType.PROPOSAL_RECEIVED.value
        )
    ).scalars().all()
    assert len(events) == 1


def test_publishing_a_job_notifies_the_client(db, client_user):
    job = _make_draft_job(db, client_user)

    job_service.change_status(db, client_user, job.id, JobStatus.PUBLISHED)

    events = db.execute(
        select(NotificationEvent).where(
            NotificationEvent.event_type == NotificationEventType.JOB_PUBLISHED.value
        )
    ).scalars().all()

    assert len(events) == 1
    assert events[0].recipient_id == client_user.id
    assert events[0].payload["job_title"] == job.title


def test_closing_a_job_notifies_the_client(db, client_user):
    job = _make_job(db, client_user)  # already PUBLISHED

    job_service.change_status(db, client_user, job.id, JobStatus.CLOSED)

    events = db.execute(
        select(NotificationEvent).where(
            NotificationEvent.event_type == NotificationEventType.JOB_CLOSED.value
        )
    ).scalars().all()

    assert len(events) == 1
    assert events[0].recipient_id == client_user.id
    assert events[0].payload["job_title"] == job.title


def test_publishing_two_jobs_creates_two_separate_notifications(db, client_user):
    # Confirms JOB_PUBLISHED idempotency keys are per-job, not accidentally
    # deduplicated across different jobs.
    job_a = _make_draft_job(db, client_user, title="Job A")
    job_b = _make_draft_job(db, client_user, title="Job B")

    job_service.change_status(db, client_user, job_a.id, JobStatus.PUBLISHED)
    job_service.change_status(db, client_user, job_b.id, JobStatus.PUBLISHED)

    events = db.execute(
        select(NotificationEvent).where(
            NotificationEvent.event_type == NotificationEventType.JOB_PUBLISHED.value
        )
    ).scalars().all()

    assert len(events) == 2
    assert {e.payload["job_title"] for e in events} == {"Job A", "Job B"}


def test_job_creation_itself_emits_no_notification(db, client_user):
    
    before = len(db.execute(select(NotificationEvent)).scalars().all())

    job_service.create_job(
        db,
        client_user,
        JobCreateRequest(
            title="Quiet job",
            description="No notification expected",
            rate_type=RateType.FIXED,
            budget_min=10,
            budget_max=20,
            skill_ids=[],
        ),
    )

    after = len(db.execute(select(NotificationEvent)).scalars().all())
    assert after == before





def test_list_notifications_returns_only_your_own(db, client_user, freelancer_user, as_user):
    _emit_simple(freelancer_user, key_suffix="mine")
    notification_service.emit(
        NotificationEventType.PROPOSAL_REJECTED,
        client_user.id,
        {"job_title": "Someone else's job"},
        idempotency_key="PROPOSAL_REJECTED:theirs",
    )

    response = as_user(freelancer_user).get("/api/notifications")
    assert response.status_code == 200

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["payload"]["job_title"] == "Build an API"


def test_notification_history_never_exposes_the_real_destination(db, freelancer_user, as_user):
    _emit_simple(freelancer_user)

    response = as_user(freelancer_user).get("/api/notifications")
    delivery = response.json()["items"][0]["deliveries"][0]

    assert "***" in delivery["destination_masked"]
    assert freelancer_user.email not in response.text


def test_notifications_require_authentication(anon_client):
    assert anon_client.get("/api/notifications").status_code == 401


def test_get_and_patch_preferences(db, freelancer_user, as_user):
    client = as_user(freelancer_user)

    assert client.get("/api/notifications/preferences").status_code == 200

    response = client.patch(
        "/api/notifications/preferences",
        json={"preferences": [{"category": "PROPOSAL", "channel": "EMAIL", "enabled": False}]},
    )
    assert response.status_code == 200

    updated = {
        (row["category"], row["channel"]): row["enabled"] for row in response.json()
    }
    assert updated[("PROPOSAL", "EMAIL")] is False

    stored = db.execute(select(NotificationPreference)).scalars().all()
    assert len(stored) == 1
    assert stored[0].enabled is False


def test_mandatory_category_cannot_be_disabled(freelancer_user, as_user):
    response = as_user(freelancer_user).patch(
        "/api/notifications/preferences",
        json={"preferences": [{"category": "CONTRACT", "channel": "EMAIL", "enabled": False}]},
    )
    assert response.status_code == 422


def test_test_endpoint_sends_only_to_the_caller(db, freelancer_user, as_user, email_provider):
    response = as_user(freelancer_user).post("/api/notifications/test", json={})
    assert response.status_code == 200

    assert len(email_provider.sent) == 1
    assert email_provider.sent[0][0] == freelancer_user.email


def test_test_endpoint_is_disabled_in_production(freelancer_user, as_user, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    response = as_user(freelancer_user).post("/api/notifications/test", json={})
    assert response.status_code == 403
