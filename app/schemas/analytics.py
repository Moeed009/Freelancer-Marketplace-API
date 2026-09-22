from datetime import date

from pydantic import BaseModel


class ClientDashboard(BaseModel):
    role: str
    jobs_posted: int
    published_jobs: int
    closed_jobs: int
    job_publication_rate: float
    proposals_received: int
    accepted_proposals: int
    proposal_acceptance_rate: float
    average_proposals_per_job: float
    contracts: int
    completed_contracts: int
    contract_completion_rate: float
    average_review_rating: float | None
    completed_contract_value: float


class FreelancerDashboard(BaseModel):
    role: str
    proposals_submitted: int
    accepted_proposals: int
    rejected_proposals: int
    proposal_success_rate: float
    contracts_won: int
    completed_contracts: int
    contract_completion_rate: float
    average_rating: float | None
    completed_contract_value: float


class PerformanceAnalytics(BaseModel):
    role: str
    average_job_to_first_proposal_hours: float | None
    average_proposal_to_contract_completion_hours: float | None
    milestone_approval_rate: float
    milestone_rejection_rate: float
    milestone_overdue_rate: float
    average_milestone_approval_hours: float | None


class TrendItem(BaseModel):
    period: str
    jobs: int = 0
    proposals: int = 0
    contracts: int = 0


class AnalyticsTrendsResponse(BaseModel):
    period: str
    from_date: date
    to_date: date
    data: list[TrendItem]


class ContractAnalytics(BaseModel):
    active_contracts: int
    completed_contracts: int
    cancelled_contracts: int
    contract_completion_rate: float
    completed_contract_value: float
    milestones_total: int
    milestones_submitted: int
    milestones_approved: int
    milestones_rejected: int
    milestones_overdue: int
    milestone_approval_rate: float
    milestone_rejection_rate: float
    milestone_overdue_rate: float


class SkillAnalyticsItem(BaseModel):
    skill: str
    job_count: int
    proposal_count: int
    accepted_proposals: int
    contract_count: int


class SkillAnalyticsResponse(BaseModel):
    skills: list[SkillAnalyticsItem]