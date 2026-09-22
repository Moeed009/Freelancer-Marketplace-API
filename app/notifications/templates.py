from dataclasses import dataclass
from string import Template

from app.models.enums import NotificationChannel, NotificationEventType


class TemplateRenderError(Exception):
    """Raised when an email notification template cannot be rendered."""


@dataclass(frozen=True)
class RenderedMessage:
    subject: str
    body: str


_EMAIL_TEMPLATES: dict[NotificationEventType, tuple[str, str]] = {
    NotificationEventType.USER_REGISTERED: (
        "Welcome to $app_name",
        """Hi $full_name,

Welcome to $app_name.

Your account has been successfully created and is ready to use. You can now post jobs, discover opportunities, and manage your freelance work from your account.

We're glad to have you with us.

Best regards,
The $app_name Team""",
    ),
    NotificationEventType.LOGIN_DETECTED: (
        "New sign-in detected on your $app_name account",
        """Hi $full_name,

We detected a new sign-in to your $app_name account.

If this was you, no action is required.

If you don't recognize this activity, please secure your account immediately by changing your password and reviewing your account activity.

Best regards,
The $app_name Security Team""",
    ),
    NotificationEventType.JOB_PUBLISHED: (
        "Your job is now live: $job_title",
        """Hi,

Your job "$job_title" has been successfully published.

It is now visible to freelancers who may be interested in your project.

You can review proposals and manage your job from your dashboard.

Best regards,
The $app_name Team""",
    ),
    NotificationEventType.JOB_CLOSED: (
        "Your job has been closed: $job_title",
        """Hi,

Your job "$job_title" has been successfully closed.

The job is no longer accepting new proposals.

You can review its details and previous proposals from your dashboard.

Best regards,
The $app_name Team""",
    ),
    NotificationEventType.PROPOSAL_RECEIVED: (
        "New proposal received for: $job_title",
        """Hi,

You have received a new proposal for your job "$job_title".

Freelancer: $freelancer_name
Bid amount: $bid_amount

Please sign in to your dashboard to review the proposal and decide how you would like to proceed.

Best regards,
The $app_name Team""",
    ),
    NotificationEventType.PROPOSAL_ACCEPTED: (
        "Your proposal has been accepted: $job_title",
        """Congratulations!

Your proposal for "$job_title" has been accepted.

A contract has been created, and you can now review the contract details from your dashboard.

We wish you a successful project.

Best regards,
The $app_name Team""",
    ),
    NotificationEventType.PROPOSAL_REJECTED: (
        "Update regarding your proposal: $job_title",
        """Hi,

Thank you for your interest in the project "$job_title".

The client has decided not to proceed with your proposal at this time.

Don't be discouraged. Continue exploring new opportunities and submitting proposals that match your skills and experience.

Best regards,
The $app_name Team""",
    ),
    NotificationEventType.CONTRACT_CREATED: (
        "New contract created: $job_title",
        """Hi,

A new contract has been created for "$job_title".

Agreed amount: $agreed_amount

Please sign in to your dashboard to review the contract details, milestones, and other project information.

Best regards,
The $app_name Team""",
    ),
    NotificationEventType.CONTRACT_COMPLETED: (
        "Contract completed: $job_title",
        """Hi,

The contract for "$job_title" has been marked as completed.

You can now review the completed project and leave feedback for the other party from your dashboard.

Thank you for using $app_name.

Best regards,
The $app_name Team""",
    ),
    NotificationEventType.CONTRACT_CANCELLED: (
        "Contract cancelled: $job_title",
        """Hi,

The contract for "$job_title" has been cancelled.

Please sign in to your dashboard if you need to review the contract details or related activity.

Best regards,
The $app_name Team""",
    ),
    NotificationEventType.MILESTONE_SUBMITTED: (
        "Milestone submitted for review: $milestone_title",
        """Hi,

The milestone "$milestone_title" has been submitted and is now waiting for your review.

Please sign in to your dashboard to review the submitted milestone and take the appropriate action.

Best regards,
The $app_name Team""",
    ),
    NotificationEventType.MILESTONE_APPROVED: (
        "Milestone approved: $milestone_title",
        """Congratulations!

Your milestone "$milestone_title" has been approved.

You can sign in to your dashboard to review the updated milestone and contract status.

Best regards,
The $app_name Team""",
    ),
    NotificationEventType.MILESTONE_REJECTED: (
        "Milestone requires changes: $milestone_title",
        """Hi,

Your milestone "$milestone_title" has been reviewed and requires changes before it can be approved.

Please sign in to your dashboard to review the feedback and make the necessary updates.

Best regards,
The $app_name Team""",
    ),
    NotificationEventType.REVIEW_RECEIVED: (
        "You received a new review",
        """Hi,

$reviewer_name has left you a $rating-star review on $app_name.

Sign in to your dashboard to view the review and see your latest feedback.

Thank you for being part of the $app_name community.

Best regards,
The $app_name Team""",
    ),
}


def has_template(
    event_type: NotificationEventType,
    channel: NotificationChannel,
) -> bool:
    if channel is not NotificationChannel.EMAIL:
        return False

    return event_type in _EMAIL_TEMPLATES


def _substitute(template_str: str, variables: dict) -> str:
    try:
        return Template(template_str).substitute(variables)
    except KeyError as exc:
        raise TemplateRenderError(
            f"Missing template variable: {exc.args[0]}"
        ) from exc
    except ValueError as exc:
        raise TemplateRenderError(
            f"Malformed template: {exc}"
        ) from exc


def render(
    event_type: NotificationEventType,
    channel: NotificationChannel,
    payload: dict,
    app_name: str,
) -> RenderedMessage:
    if channel is not NotificationChannel.EMAIL:
        raise TemplateRenderError(
            f"Unsupported notification channel: {channel.value}"
        )

    variables = {
        key: str(value)
        for key, value in payload.items()
    }
    variables.setdefault("app_name", app_name)

    template_pair = _EMAIL_TEMPLATES.get(event_type)

    if template_pair is None:
        raise TemplateRenderError(
            f"No EMAIL template for {event_type.value}"
        )

    subject_template, body_template = template_pair

    return RenderedMessage(
        subject=_substitute(subject_template, variables),
        body=_substitute(body_template, variables),
    )
