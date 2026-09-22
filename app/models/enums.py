import enum


class UserRole(str, enum.Enum):
    CLIENT = "CLIENT"
    FREELANCER = "FREELANCER"


class AvailabilityStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class RateType(str, enum.Enum):
    FIXED = "FIXED"
    HOURLY = "HOURLY"


class JobStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"


class ProposalStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class ContractStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MilestoneStatus(str, enum.Enum):
    PENDING = "PENDING"       
    SUBMITTED = "SUBMITTED"    
    APPROVED = "APPROVED"      
    REJECTED = "REJECTED"      





class NotificationChannel(str, enum.Enum):
    
    EMAIL = "EMAIL"
    SMS = "SMS"


class NotificationCategory(str, enum.Enum):
    

    ACCOUNT = "ACCOUNT"
    SECURITY = "SECURITY"
    JOB = "JOB"
    PROPOSAL = "PROPOSAL"
    CONTRACT = "CONTRACT"
    MILESTONE = "MILESTONE"
    REVIEW = "REVIEW"


class NotificationEventType(str, enum.Enum):
    

    USER_REGISTERED = "USER_REGISTERED"
    LOGIN_DETECTED = "LOGIN_DETECTED"

    JOB_PUBLISHED = "JOB_PUBLISHED"
    JOB_CLOSED = "JOB_CLOSED"

    PROPOSAL_RECEIVED = "PROPOSAL_RECEIVED"
    PROPOSAL_ACCEPTED = "PROPOSAL_ACCEPTED"
    PROPOSAL_REJECTED = "PROPOSAL_REJECTED"

    CONTRACT_CREATED = "CONTRACT_CREATED"
    CONTRACT_COMPLETED = "CONTRACT_COMPLETED"
    CONTRACT_CANCELLED = "CONTRACT_CANCELLED"

    MILESTONE_SUBMITTED = "MILESTONE_SUBMITTED"
    MILESTONE_APPROVED = "MILESTONE_APPROVED"
    MILESTONE_REJECTED = "MILESTONE_REJECTED"

    REVIEW_RECEIVED = "REVIEW_RECEIVED"


class DeliveryStatus(str, enum.Enum):
   

    PENDING = "PENDING"    
    SENT = "SENT"          
    FAILED = "FAILED"      
    SKIPPED = "SKIPPED"
    
class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
    