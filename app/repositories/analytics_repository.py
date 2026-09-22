from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from app.models.contract import Contract
from app.models.enums import (
    ContractStatus,
    JobStatus,
    MilestoneStatus,
    ProposalStatus,
    UserRole,
)
from app.models.job import Job
from app.models.job_skill import JobSkill
from app.models.milestone import Milestone
from app.models.proposal import Proposal
from app.models.review import Review
from app.models.skill import Skill


class AnalyticsRepository:

    @staticmethod
    def _start_datetime(value: date) -> datetime:
        return datetime.combine(value, time.min, tzinfo=timezone.utc)

    @staticmethod
    def _end_datetime(value: date) -> datetime:
        return datetime.combine(value + timedelta(days=1), time.min, tzinfo=timezone.utc)

    @staticmethod
    def _percentage(numerator: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0
        return round((numerator / denominator) * 100, 2)

    @staticmethod
    def _average(value) -> float | None:
        if value is None:
            return None
        return round(float(value), 2)

    @staticmethod
    def _hours_expression(db: Session, start_column, end_column):
        if db.bind.dialect.name == "sqlite":
            return (func.julianday(end_column) - func.julianday(start_column)) * 24
        return func.extract("epoch", end_column - start_column) / 3600

    @staticmethod
    def get_client_dashboard(db: Session, user_id, from_date: date | None = None, to_date: date | None = None):
        job_filters = [Job.client_id == user_id]
        if from_date:
            job_filters.append(Job.created_at >= AnalyticsRepository._start_datetime(from_date))
        if to_date:
            job_filters.append(Job.created_at < AnalyticsRepository._end_datetime(to_date))
        jobs = db.execute(
            select(
                func.count(Job.id),
                func.count(case((Job.status == JobStatus.PUBLISHED, 1))),
                func.count(case((Job.status == JobStatus.CLOSED, 1))),
            ).where(*job_filters)
        ).one()
        proposal_filters = [Job.client_id == user_id]
        if from_date:
            proposal_filters.append(Proposal.created_at >= AnalyticsRepository._start_datetime(from_date))
        if to_date:
            proposal_filters.append(Proposal.created_at < AnalyticsRepository._end_datetime(to_date))
        proposals = db.execute(
            select(
                func.count(Proposal.id),
                func.count(case((Proposal.status == ProposalStatus.ACCEPTED, 1))),
            )
            .join(Job, Proposal.job_id == Job.id)
            .where(*proposal_filters)
        ).one()
        contract_filters = [Contract.client_id == user_id]
        if from_date:
            contract_filters.append(Contract.created_at >= AnalyticsRepository._start_datetime(from_date))
        if to_date:
            contract_filters.append(Contract.created_at < AnalyticsRepository._end_datetime(to_date))
        contracts = db.execute(
            select(
                func.count(Contract.id),
                func.count(case((Contract.status == ContractStatus.COMPLETED, 1))),
                func.coalesce(
                    func.sum(case((Contract.status == ContractStatus.COMPLETED, Contract.agreed_amount), else_=0)),
                    0,
                ),
            ).where(*contract_filters)
        ).one()
        rating_filters = [Contract.client_id == user_id]
        if from_date:
            rating_filters.append(Review.created_at >= AnalyticsRepository._start_datetime(from_date))
        if to_date:
            rating_filters.append(Review.created_at < AnalyticsRepository._end_datetime(to_date))
        rating = db.execute(
            select(func.avg(Review.rating))
            .join(Contract, Review.contract_id == Contract.id)
            .where(*rating_filters)
        ).scalar()
        jobs_posted = jobs[0] or 0
        published_jobs = jobs[1] or 0
        closed_jobs = jobs[2] or 0
        proposals_received = proposals[0] or 0
        accepted_proposals = proposals[1] or 0
        total_contracts = contracts[0] or 0
        completed_contracts = contracts[1] or 0
        return {
            "role": UserRole.CLIENT.value,
            "jobs_posted": jobs_posted,
            "published_jobs": published_jobs,
            "closed_jobs": closed_jobs,
            "job_publication_rate": AnalyticsRepository._percentage(published_jobs, jobs_posted),
            "proposals_received": proposals_received,
            "accepted_proposals": accepted_proposals,
            "proposal_acceptance_rate": AnalyticsRepository._percentage(accepted_proposals, proposals_received),
            "average_proposals_per_job": round(proposals_received / jobs_posted, 2) if jobs_posted else 0.0,
            "contracts": total_contracts,
            "completed_contracts": completed_contracts,
            "contract_completion_rate": AnalyticsRepository._percentage(completed_contracts, total_contracts),
            "average_review_rating": AnalyticsRepository._average(rating),
            "completed_contract_value": float(contracts[2] or 0),
        }

    @staticmethod
    def get_freelancer_dashboard(db: Session, user_id, from_date: date | None = None, to_date: date | None = None):
        proposal_filters = [Proposal.freelancer_id == user_id]
        if from_date:
            proposal_filters.append(Proposal.created_at >= AnalyticsRepository._start_datetime(from_date))
        if to_date:
            proposal_filters.append(Proposal.created_at < AnalyticsRepository._end_datetime(to_date))
        proposals = db.execute(
            select(
                func.count(Proposal.id),
                func.count(case((Proposal.status == ProposalStatus.ACCEPTED, 1))),
                func.count(case((Proposal.status == ProposalStatus.REJECTED, 1))),
            ).where(*proposal_filters)
        ).one()
        contract_filters = [Contract.freelancer_id == user_id]
        if from_date:
            contract_filters.append(Contract.created_at >= AnalyticsRepository._start_datetime(from_date))
        if to_date:
            contract_filters.append(Contract.created_at < AnalyticsRepository._end_datetime(to_date))
        contracts = db.execute(
            select(
                func.count(Contract.id),
                func.count(case((Contract.status == ContractStatus.COMPLETED, 1))),
                func.coalesce(
                    func.sum(case((Contract.status == ContractStatus.COMPLETED, Contract.agreed_amount), else_=0)),
                    0,
                ),
            ).where(*contract_filters)
        ).one()
        review_filters = [Review.reviewee_id == user_id]
        if from_date:
            review_filters.append(Review.created_at >= AnalyticsRepository._start_datetime(from_date))
        if to_date:
            review_filters.append(Review.created_at < AnalyticsRepository._end_datetime(to_date))
        rating = db.execute(select(func.avg(Review.rating)).where(*review_filters)).scalar()
        total_proposals = proposals[0] or 0
        accepted_proposals = proposals[1] or 0
        rejected_proposals = proposals[2] or 0
        total_contracts = contracts[0] or 0
        completed_contracts = contracts[1] or 0
        return {
            "role": UserRole.FREELANCER.value,
            "proposals_submitted": total_proposals,
            "accepted_proposals": accepted_proposals,
            "rejected_proposals": rejected_proposals,
            "proposal_success_rate": AnalyticsRepository._percentage(accepted_proposals, total_proposals),
            "contracts_won": total_contracts,
            "completed_contracts": completed_contracts,
            "contract_completion_rate": AnalyticsRepository._percentage(completed_contracts, total_contracts),
            "average_rating": AnalyticsRepository._average(rating),
            "completed_contract_value": float(contracts[2] or 0),
        }

    @staticmethod
    def get_client_performance(db: Session, user_id, from_date: date | None = None, to_date: date | None = None):
        first_proposal_subquery = (
            select(Proposal.job_id.label("job_id"), func.min(Proposal.created_at).label("first_proposal_at"))
            .join(Job, Proposal.job_id == Job.id)
            .where(Job.client_id == user_id, Job.published_at.is_not(None), Proposal.created_at >= Job.published_at)
            .group_by(Proposal.job_id)
            .subquery()
        )
        first_proposal_time = AnalyticsRepository._hours_expression(
            db, Job.published_at, first_proposal_subquery.c.first_proposal_at
        )
        first_proposal = db.execute(
            select(func.avg(first_proposal_time))
            .select_from(Job)
            .join(first_proposal_subquery, first_proposal_subquery.c.job_id == Job.id)
            .where(
                Job.client_id == user_id,
                Job.published_at.is_not(None),
                *([Job.published_at >= AnalyticsRepository._start_datetime(from_date)] if from_date else []),
                *([Job.published_at < AnalyticsRepository._end_datetime(to_date)] if to_date else []),
            )
        ).scalar()
        completion_time = AnalyticsRepository._hours_expression(db, Proposal.accepted_at, Contract.completed_at)
        completion_filters = [
            Job.client_id == user_id,
            Proposal.accepted_at.is_not(None),
            Contract.completed_at.is_not(None),
        ]
        if from_date:
            completion_filters.append(Contract.completed_at >= AnalyticsRepository._start_datetime(from_date))
        if to_date:
            completion_filters.append(Contract.completed_at < AnalyticsRepository._end_datetime(to_date))
        completion = db.execute(
            select(func.avg(completion_time))
            .select_from(Proposal)
            .join(Contract, Contract.proposal_id == Proposal.id)
            .join(Job, Proposal.job_id == Job.id)
            .where(*completion_filters)
        ).scalar()
        return AnalyticsRepository._build_performance(
            db, user_id, UserRole.CLIENT, first_proposal, completion, from_date, to_date
        )

    @staticmethod
    def get_freelancer_performance(db: Session, user_id, from_date: date | None = None, to_date: date | None = None):
        first_proposal_time = AnalyticsRepository._hours_expression(db, Job.published_at, Proposal.created_at)
        first_proposal = db.execute(
            select(func.avg(first_proposal_time))
            .select_from(Proposal)
            .join(Job, Proposal.job_id == Job.id)
            .where(
                Proposal.freelancer_id == user_id,
                Job.published_at.is_not(None),
                Proposal.created_at >= Job.published_at,
                *([Proposal.created_at >= AnalyticsRepository._start_datetime(from_date)] if from_date else []),
                *([Proposal.created_at < AnalyticsRepository._end_datetime(to_date)] if to_date else []),
            )
        ).scalar()
        completion_time = AnalyticsRepository._hours_expression(db, Proposal.accepted_at, Contract.completed_at)
        completion = db.execute(
            select(func.avg(completion_time))
            .select_from(Proposal)
            .join(Contract, Contract.proposal_id == Proposal.id)
            .where(
                Proposal.freelancer_id == user_id,
                Proposal.accepted_at.is_not(None),
                Contract.completed_at.is_not(None),
                *([Contract.completed_at >= AnalyticsRepository._start_datetime(from_date)] if from_date else []),
                *([Contract.completed_at < AnalyticsRepository._end_datetime(to_date)] if to_date else []),
            )
        ).scalar()
        return AnalyticsRepository._build_performance(
            db, user_id, UserRole.FREELANCER, first_proposal, completion, from_date, to_date
        )

    @staticmethod
    def _build_performance(db: Session, user_id, role: UserRole, first_proposal, completion, from_date, to_date):
        if role == UserRole.CLIENT:
            contract_scope = Contract.client_id == user_id
        else:
            contract_scope = Contract.freelancer_id == user_id
        milestone_filters = [contract_scope]
        if from_date:
            milestone_filters.append(Milestone.created_at >= AnalyticsRepository._start_datetime(from_date))
        if to_date:
            milestone_filters.append(Milestone.created_at < AnalyticsRepository._end_datetime(to_date))
        milestone_result = db.execute(
            select(
                func.count(Milestone.id),
                func.count(case((Milestone.status == MilestoneStatus.APPROVED, 1))),
                func.count(case((Milestone.status == MilestoneStatus.REJECTED, 1))),
                func.count(
                    case(
                        (
                            (Milestone.due_date < func.current_date())
                            & (Milestone.status != MilestoneStatus.APPROVED),
                            1,
                        )
                    )
                ),
            )
            .select_from(Milestone)
            .join(Contract, Milestone.contract_id == Contract.id)
            .where(*milestone_filters)
        ).one()
        approval_hours = AnalyticsRepository._hours_expression(db, Milestone.submitted_at, Milestone.approved_at)
        approval_timing = db.execute(
            select(func.avg(approval_hours))
            .select_from(Milestone)
            .join(Contract, Milestone.contract_id == Contract.id)
            .where(
                contract_scope,
                Milestone.submitted_at.is_not(None),
                Milestone.approved_at.is_not(None),
                *([Milestone.approved_at >= AnalyticsRepository._start_datetime(from_date)] if from_date else []),
                *([Milestone.approved_at < AnalyticsRepository._end_datetime(to_date)] if to_date else []),
            )
        ).scalar()
        total = milestone_result[0] or 0
        approved = milestone_result[1] or 0
        rejected = milestone_result[2] or 0
        overdue = milestone_result[3] or 0
        decision_count = approved + rejected
        return {
            "role": role.value,
            "average_job_to_first_proposal_hours": (
                round(float(first_proposal), 2) if first_proposal is not None else None
            ),
            "average_proposal_to_contract_completion_hours": (
                round(float(completion), 2) if completion is not None else None
            ),
            "milestone_approval_rate": AnalyticsRepository._percentage(approved, decision_count),
            "milestone_rejection_rate": AnalyticsRepository._percentage(rejected, decision_count),
            "milestone_overdue_rate": AnalyticsRepository._percentage(overdue, total),
            "average_milestone_approval_hours": (
                round(float(approval_timing), 2) if approval_timing is not None else None
            ),
        }

    @staticmethod
    def get_client_trends(db: Session, user_id, from_date: date, to_date: date, period: str):
        return AnalyticsRepository._get_trends(db, user_id, UserRole.CLIENT, from_date, to_date, period)

    @staticmethod
    def get_freelancer_trends(db: Session, user_id, from_date: date, to_date: date, period: str):
        return AnalyticsRepository._get_trends(db, user_id, UserRole.FREELANCER, from_date, to_date, period)

    @staticmethod
    def _get_trends(db: Session, user_id, role: UserRole, from_date: date, to_date: date, period: str):
        start = AnalyticsRepository._start_datetime(from_date)
        end = AnalyticsRepository._end_datetime(to_date)
        data = AnalyticsRepository._empty_periods(from_date, to_date, period)
        if db.bind.dialect.name == "postgresql":
            job_period = func.date_trunc(period, Job.created_at)
            proposal_period = func.date_trunc(period, Proposal.created_at)
            contract_period = func.date_trunc(period, Contract.created_at)
        else:
            if period == "day":
                job_period = func.date(Job.created_at)
                proposal_period = func.date(Proposal.created_at)
                contract_period = func.date(Contract.created_at)
            elif period == "month":
                job_period = func.strftime("%Y-%m-01", Job.created_at)
                proposal_period = func.strftime("%Y-%m-01", Proposal.created_at)
                contract_period = func.strftime("%Y-%m-01", Contract.created_at)
            else:
                job_period = func.strftime("%Y-%W-1", Job.created_at)
                proposal_period = func.strftime("%Y-%W-1", Proposal.created_at)
                contract_period = func.strftime("%Y-%W-1", Contract.created_at)
        if role == UserRole.CLIENT:
            job_rows = db.execute(
                select(job_period.label("period"), func.count(Job.id))
                .where(Job.client_id == user_id, Job.created_at >= start, Job.created_at < end)
                .group_by(job_period)
            ).all()
            proposal_rows = db.execute(
                select(proposal_period.label("period"), func.count(Proposal.id))
                .select_from(Proposal)
                .join(Job, Proposal.job_id == Job.id)
                .where(Job.client_id == user_id, Proposal.created_at >= start, Proposal.created_at < end)
                .group_by(proposal_period)
            ).all()
            contract_rows = db.execute(
                select(contract_period.label("period"), func.count(Contract.id))
                .where(Contract.client_id == user_id, Contract.created_at >= start, Contract.created_at < end)
                .group_by(contract_period)
            ).all()
        else:
            job_rows = []
            proposal_rows = db.execute(
                select(proposal_period.label("period"), func.count(Proposal.id))
                .where(
                    Proposal.freelancer_id == user_id,
                    Proposal.created_at >= start,
                    Proposal.created_at < end,
                )
                .group_by(proposal_period)
            ).all()
            contract_rows = db.execute(
                select(contract_period.label("period"), func.count(Contract.id))
                .where(
                    Contract.freelancer_id == user_id,
                    Contract.created_at >= start,
                    Contract.created_at < end,
                )
                .group_by(contract_period)
            ).all()
        for row in job_rows:
            key = AnalyticsRepository._period_key(row[0], period)
            if key in data:
                data[key]["jobs"] = row[1] or 0
        for row in proposal_rows:
            key = AnalyticsRepository._period_key(row[0], period)
            if key in data:
                data[key]["proposals"] = row[1] or 0
        for row in contract_rows:
            key = AnalyticsRepository._period_key(row[0], period)
            if key in data:
                data[key]["contracts"] = row[1] or 0
        return list(data.values())

    @staticmethod
    def _period_key(value, period: str) -> str:
        if isinstance(value, str):
            if period == "month":
                return value[:7]
            if period == "week":
                parts = value.split("-")
                if len(parts) >= 2:
                    return f"{parts[0]}-W{parts[1]}"
            return value[:10]
        if period == "day":
            return value.strftime("%Y-%m-%d")
        if period == "month":
            return value.strftime("%Y-%m")
        return value.strftime("%Y-W%W")

    @staticmethod
    def _empty_periods(from_date: date, to_date: date, period: str):
        result = {}
        current = from_date
        while current <= to_date:
            if period == "day":
                key = current.strftime("%Y-%m-%d")
                current += timedelta(days=1)
            elif period == "week":
                week_start = current - timedelta(days=current.weekday())
                key = week_start.strftime("%Y-W%W")
                current = week_start + timedelta(days=7)
            else:
                key = current.strftime("%Y-%m")
                if current.month == 12:
                    current = date(current.year + 1, 1, 1)
                else:
                    current = date(current.year, current.month + 1, 1)
            if key not in result:
                result[key] = {"period": key, "jobs": 0, "proposals": 0, "contracts": 0}
        return result

    @staticmethod
    def get_client_contracts(db: Session, user_id, from_date: date | None = None, to_date: date | None = None):
        return AnalyticsRepository._get_contracts(db, user_id, UserRole.CLIENT, from_date, to_date)

    @staticmethod
    def get_freelancer_contracts(db: Session, user_id, from_date: date | None = None, to_date: date | None = None):
        return AnalyticsRepository._get_contracts(db, user_id, UserRole.FREELANCER, from_date, to_date)

    @staticmethod
    def _get_contracts(db: Session, user_id, role: UserRole, from_date: date | None, to_date: date | None):
        owner_column = Contract.client_id if role == UserRole.CLIENT else Contract.freelancer_id
        contract_filters = [owner_column == user_id]
        if from_date:
            contract_filters.append(Contract.created_at >= AnalyticsRepository._start_datetime(from_date))
        if to_date:
            contract_filters.append(Contract.created_at < AnalyticsRepository._end_datetime(to_date))
        contracts = db.execute(
            select(
                func.count(Contract.id),
                func.count(case((Contract.status == ContractStatus.ACTIVE, 1))),
                func.count(case((Contract.status == ContractStatus.COMPLETED, 1))),
                func.count(case((Contract.status == ContractStatus.CANCELLED, 1))),
                func.coalesce(
                    func.sum(case((Contract.status == ContractStatus.COMPLETED, Contract.agreed_amount), else_=0)),
                    0,
                ),
            ).where(*contract_filters)
        ).one()
        milestone_filters = [owner_column == user_id]
        if from_date:
            milestone_filters.append(Milestone.created_at >= AnalyticsRepository._start_datetime(from_date))
        if to_date:
            milestone_filters.append(Milestone.created_at < AnalyticsRepository._end_datetime(to_date))
        milestones = db.execute(
            select(
                func.count(Milestone.id),
                func.count(case((Milestone.status == MilestoneStatus.SUBMITTED, 1))),
                func.count(case((Milestone.status == MilestoneStatus.APPROVED, 1))),
                func.count(case((Milestone.status == MilestoneStatus.REJECTED, 1))),
                func.count(
                    case(
                        (
                            (Milestone.due_date < func.current_date())
                            & (Milestone.status != MilestoneStatus.APPROVED),
                            1,
                        )
                    )
                ),
            )
            .select_from(Milestone)
            .join(Contract, Milestone.contract_id == Contract.id)
            .where(*milestone_filters)
        ).one()
        total_contracts = contracts[0] or 0
        completed_contracts = contracts[2] or 0
        total_milestones = milestones[0] or 0
        approved = milestones[2] or 0
        rejected = milestones[3] or 0
        overdue = milestones[4] or 0
        decision_count = approved + rejected
        return {
            "active_contracts": contracts[1] or 0,
            "completed_contracts": completed_contracts,
            "cancelled_contracts": contracts[3] or 0,
            "contract_completion_rate": AnalyticsRepository._percentage(completed_contracts, total_contracts),
            "completed_contract_value": float(contracts[4] or 0),
            "milestones_total": total_milestones,
            "milestones_submitted": milestones[1] or 0,
            "milestones_approved": approved,
            "milestones_rejected": rejected,
            "milestones_overdue": overdue,
            "milestone_approval_rate": AnalyticsRepository._percentage(approved, decision_count),
            "milestone_rejection_rate": AnalyticsRepository._percentage(rejected, decision_count),
            "milestone_overdue_rate": AnalyticsRepository._percentage(overdue, total_milestones),
        }

    @staticmethod
    def get_skills(db: Session, user_id, role: str, from_date: date | None = None, to_date: date | None = None):
        if role == UserRole.CLIENT.value:
            filters = [Job.client_id == user_id]
            if from_date:
                filters.append(Job.created_at >= AnalyticsRepository._start_datetime(from_date))
            if to_date:
                filters.append(Job.created_at < AnalyticsRepository._end_datetime(to_date))
            result = db.execute(
                select(
                    Skill.name,
                    func.count(func.distinct(Job.id)).label("job_count"),
                    func.count(func.distinct(Proposal.id)).label("proposal_count"),
                    func.count(
                        func.distinct(case((Proposal.status == ProposalStatus.ACCEPTED, Proposal.id)))
                    ).label("accepted_proposals"),
                    func.count(func.distinct(Contract.id)).label("contract_count"),
                )
                .select_from(Skill)
                .join(JobSkill, JobSkill.skill_id == Skill.id)
                .join(Job, Job.id == JobSkill.job_id)
                .outerjoin(Proposal, Proposal.job_id == Job.id)
                .outerjoin(Contract, Contract.job_id == Job.id)
                .where(*filters)
                .group_by(Skill.id, Skill.name)
                .order_by(func.count(func.distinct(Job.id)).desc(), Skill.name.asc())
            ).all()
        else:
            filters = [Proposal.freelancer_id == user_id]
            if from_date:
                filters.append(Proposal.created_at >= AnalyticsRepository._start_datetime(from_date))
            if to_date:
                filters.append(Proposal.created_at < AnalyticsRepository._end_datetime(to_date))
            result = db.execute(
                select(
                    Skill.name,
                    func.count(func.distinct(Job.id)).label("job_count"),
                    func.count(func.distinct(Proposal.id)).label("proposal_count"),
                    func.count(
                        func.distinct(case((Proposal.status == ProposalStatus.ACCEPTED, Proposal.id)))
                    ).label("accepted_proposals"),
                    func.count(func.distinct(Contract.id)).label("contract_count"),
                )
                .select_from(Skill)
                .join(JobSkill, JobSkill.skill_id == Skill.id)
                .join(Job, Job.id == JobSkill.job_id)
                .join(Proposal, Proposal.job_id == Job.id)
                .outerjoin(Contract, Contract.proposal_id == Proposal.id)
                .where(*filters)
                .group_by(Skill.id, Skill.name)
                .order_by(func.count(func.distinct(Proposal.id)).desc(), Skill.name.asc())
            ).all()
        return [
            {
                "skill": row.name,
                "job_count": row.job_count or 0,
                "proposal_count": row.proposal_count or 0,
                "accepted_proposals": row.accepted_proposals or 0,
                "contract_count": row.contract_count or 0,
            }
            for row in result
        ]