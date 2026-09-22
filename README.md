# Freelancer-Marketplace-API
Freelancer Marketplace API — A scalable Upwork-style freelance platform backend built with FastAPI, PostgreSQL, Supabase Authentication, SQLAlchemy, Alembic, Pydantic, and Pytest. Supports clients and freelancers with jobs, proposals, contracts, milestones, profiles, skills, and reviews.


---

## Notifications (Track A)

Event-driven email/SMS built as a **transactional outbox**. Business services
call `notification_service.emit(...)`, which writes an event plus one delivery
row per channel; a background dispatcher drains the outbox. Nothing in the
request path ever calls a provider.

Full rationale: [DESIGN_NOTE_TRACK_A.md](./DESIGN_NOTE_TRACK_A.md)

### Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/api/notifications` | Your own history. Recipient comes from the token, never a parameter. |
| GET | `/api/notifications/preferences` | Effective preferences (stored overrides on top of catalog defaults). |
| PATCH | `/api/notifications/preferences` | Partial update by `(category, channel)`. 422 on mandatory categories. |
| POST | `/api/notifications/test` | Dev only. 403 when `ENVIRONMENT=production`. Sends to the caller only. |

### Events

`USER_REGISTERED`, `LOGIN_DETECTED`, `JOB_PUBLISHED`, `JOB_CLOSED`,
`PROPOSAL_RECEIVED`, `PROPOSAL_ACCEPTED`, `PROPOSAL_REJECTED`,
`CONTRACT_CREATED`, `CONTRACT_COMPLETED`, `CONTRACT_CANCELLED`,
`MILESTONE_SUBMITTED`, `MILESTONE_APPROVED`, `MILESTONE_REJECTED`,
`REVIEW_RECEIVED`.

Declared once in `app/notifications/events.py` (category, default channels,
required payload fields, whether users may opt out). Templates live in
`app/notifications/templates.py`.

### Supabase setup

1. Deploy an Edge Function holding the SMTP credentials:
   `supabase functions deploy send-email`
   It receives `{to, subject, body}` and returns 2xx on success. Keep SMTP
   secrets in Supabase function secrets, never in this repo.
2. Set `NOTIFICATION_EMAIL_BACKEND=supabase` and `NOTIFICATION_EMAIL_FUNCTION`.
3. For SMS, set `SMS_PROVIDER_URL`, `SMS_PROVIDER_TOKEN`, `SMS_PROVIDER_SENDER`
   and `NOTIFICATION_SMS_BACKEND=supabase`. Supabase has no generic SMS-send
   API — see the design note.

Use `console` backends for local development (messages are logged, nothing is
sent) and `memory` for tests.

### Railway

Set every variable from `.env.example` under Track A. Leave
`NOTIFICATION_WORKER_ENABLED=true` so the dispatcher runs; if you later split
the worker into its own service, run it there and set this to `false` on the web
service.

### Running the notification tests

```bash
pytest app/tests/test_notifications.py -v
```

The suite sets `NOTIFICATION_WORKER_ENABLED=false` and drives
`process_due_deliveries()` directly, so retry and backoff behaviour is asserted
without any sleeping.
