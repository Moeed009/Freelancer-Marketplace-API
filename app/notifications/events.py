
from dataclasses import dataclass

from app.core.exceptions import ValidationAppError
from app.models.enums import NotificationCategory, NotificationChannel, NotificationEventType

EMAIL = NotificationChannel.EMAIL


@dataclass(frozen=True)
class EventSpec:
    category: NotificationCategory
   
    default_channels: tuple[NotificationChannel, ...]
   
    required_fields: tuple[str, ...] = ()
   
    mandatory: bool = False


EVENT_CATALOG: dict[NotificationEventType, EventSpec] = {
    NotificationEventType.USER_REGISTERED: EventSpec(
        category=NotificationCategory.ACCOUNT,
        default_channels=(EMAIL,),
        required_fields=("full_name",),
        mandatory=True,
    ),
    NotificationEventType.LOGIN_DETECTED: EventSpec(
        category=NotificationCategory.SECURITY,
        default_channels=(EMAIL,),
        required_fields=("full_name",),
        mandatory=True, 
    ),
    NotificationEventType.JOB_PUBLISHED: EventSpec(
        category=NotificationCategory.JOB,
        default_channels=(EMAIL,),
        required_fields=("job_title",),
    ),
    NotificationEventType.JOB_CLOSED: EventSpec(
        category=NotificationCategory.JOB,
        default_channels=(EMAIL,),
        required_fields=("job_title",),
    ),
    NotificationEventType.PROPOSAL_RECEIVED: EventSpec(
        category=NotificationCategory.PROPOSAL,
        default_channels=(EMAIL,),
        required_fields=("job_title", "freelancer_name", "bid_amount"),
    ),
    NotificationEventType.PROPOSAL_ACCEPTED: EventSpec(
        category=NotificationCategory.PROPOSAL,
        default_channels=(EMAIL,),
        required_fields=("job_title",),
    ),
    NotificationEventType.PROPOSAL_REJECTED: EventSpec(
        category=NotificationCategory.PROPOSAL,
        default_channels=(EMAIL,),
        required_fields=("job_title",),
    ),
    NotificationEventType.CONTRACT_CREATED: EventSpec(
        category=NotificationCategory.CONTRACT,
        default_channels=(EMAIL,),
        required_fields=("job_title", "agreed_amount"),
        mandatory=True,  
    ),
    NotificationEventType.CONTRACT_COMPLETED: EventSpec(
        category=NotificationCategory.CONTRACT,
        default_channels=(EMAIL,),
        required_fields=("job_title",),
        mandatory=True,
    ),
    NotificationEventType.CONTRACT_CANCELLED: EventSpec(
        category=NotificationCategory.CONTRACT,
        default_channels=(EMAIL,),
        required_fields=("job_title",),
        mandatory=True,
    ),
    NotificationEventType.MILESTONE_SUBMITTED: EventSpec(
        category=NotificationCategory.MILESTONE,
        default_channels=(EMAIL,),
        required_fields=("milestone_title",),
    ),
    NotificationEventType.MILESTONE_APPROVED: EventSpec(
        category=NotificationCategory.MILESTONE,
        default_channels=(EMAIL,),
        required_fields=("milestone_title",),
    ),
    NotificationEventType.MILESTONE_REJECTED: EventSpec(
        category=NotificationCategory.MILESTONE,
        default_channels=(EMAIL,),
        required_fields=("milestone_title",),
    ),
    NotificationEventType.REVIEW_RECEIVED: EventSpec(
        category=NotificationCategory.REVIEW,
        default_channels=(EMAIL,),
        required_fields=("reviewer_name", "rating"),
    ),
}


def get_spec(event_type: NotificationEventType) -> EventSpec:
    spec = EVENT_CATALOG.get(event_type)
    if spec is None:
        raise ValidationAppError(f"Unknown notification event type: {event_type}")
    return spec


def validate_payload(event_type: NotificationEventType, payload: dict) -> None:
    
    spec = get_spec(event_type)
    missing = [field for field in spec.required_fields if field not in payload]
    if missing:
        raise ValidationAppError(
            f"Notification payload for {event_type.value} is missing: {', '.join(missing)}"
        )
