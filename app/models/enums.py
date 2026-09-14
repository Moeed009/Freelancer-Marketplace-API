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
