import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models.enums import JobStatus
from app.models.user import User
from app.repositories import job_repository, skill_repository
from app.schemas.job import JobCreateRequest, JobUpdateRequest


_ALLOWED_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.DRAFT: {JobStatus.PUBLISHED, JobStatus.CLOSED},
    JobStatus.PUBLISHED: {JobStatus.CLOSED},
    JobStatus.CLOSED: set(),
}


def _validate_skill_ids(db: Session, skill_ids: list[uuid.UUID]) -> None:
    if not skill_ids:
        return
    found = skill_repository.get_many_by_ids(db, skill_ids)
    if len(found) != len(set(skill_ids)):
        raise ValidationAppError("One or more skill_ids do not exist.")


def get_job_or_404(db: Session, job_id: uuid.UUID):
    job = job_repository.get_by_id(db, job_id)
    if job is None:
        raise NotFoundError("Job not found.")
    return job


def _assert_owner(job, client: User) -> None:
    if job.client_id != client.id:
        raise ForbiddenError("You do not own this job.")


def create_job(db: Session, client: User, data: JobCreateRequest):
    _validate_skill_ids(db, data.skill_ids)
    return job_repository.create(
        db,
        client_id=client.id,
        skill_ids=data.skill_ids,
        title=data.title,
        description=data.description,
        rate_type=data.rate_type,
        budget_min=data.budget_min,
        budget_max=data.budget_max,
        status=JobStatus.DRAFT,
    )


def update_job(db: Session, client: User, job_id: uuid.UUID, data: JobUpdateRequest):
    job = get_job_or_404(db, job_id)
    _assert_owner(job, client)

    if job.status == JobStatus.CLOSED:
        raise ValidationAppError("A closed job can no longer be edited.")
    if job.contract is not None:
        raise ValidationAppError("This job already has a contract and can no longer be edited.")

    if data.skill_ids is not None:
        _validate_skill_ids(db, data.skill_ids)

    fields = data.model_dump(exclude={"skill_ids"}, exclude_unset=True)
    if "budget_min" in fields or "budget_max" in fields:
        new_min = fields.get("budget_min", job.budget_min)
        new_max = fields.get("budget_max", job.budget_max)
        if float(new_max) < float(new_min):
            raise ValidationAppError("budget_max must be greater than or equal to budget_min")

    return job_repository.update(db, job, skill_ids=data.skill_ids, **fields)


def change_status(db: Session, client: User, job_id: uuid.UUID, new_status: JobStatus):
    job = get_job_or_404(db, job_id)
    _assert_owner(job, client)

    allowed = _ALLOWED_TRANSITIONS.get(job.status, set())
    if new_status not in allowed:
        raise ValidationAppError(f"Cannot transition job from {job.status.value} to {new_status.value}.")

    return job_repository.set_status(db, job, new_status)


def list_my_jobs(db: Session, client: User, offset: int, limit: int):
    return job_repository.list_for_client(db, client.id, offset, limit)


def delete_job(db: Session, client: User, job_id: uuid.UUID) -> None:
    job = get_job_or_404(db, job_id)
    _assert_owner(job, client)

    if job.status != JobStatus.DRAFT:
        raise ValidationAppError("Only a DRAFT job can be deleted. Close a published job instead.")
    if job.proposals:
        raise ConflictError("This job already has proposals and can no longer be deleted.")

    job_repository.delete(db, job)


def search_jobs(
    db: Session,
    *,
    keyword: str | None,
    skill_id: uuid.UUID | None,
    status: JobStatus | None,
    min_budget: float | None,
    max_budget: float | None,
    sort_by: str,
    sort_dir: str,
    offset: int,
    limit: int,
):
    return job_repository.search(
        db,
        keyword=keyword,
        skill_id=skill_id,
        status=status,
        min_budget=min_budget,
        max_budget=max_budget,
        sort_by=sort_by,
        sort_dir=sort_dir,
        offset=offset,
        limit=limit,
    )
