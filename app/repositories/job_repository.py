import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import JobStatus
from app.models.job import Job
from app.models.job_skill import JobSkill


def get_by_id(db: Session, job_id: uuid.UUID) -> Job | None:
    return db.get(Job, job_id)


def create(db: Session, *, client_id: uuid.UUID, skill_ids: list[uuid.UUID], **fields) -> Job:
    job = Job(client_id=client_id, **fields)
    db.add(job)
    db.flush()  
    for skill_id in set(skill_ids):
        db.add(JobSkill(job_id=job.id, skill_id=skill_id))
    db.commit()
    db.refresh(job)
    return job


def update(db: Session, job: Job, skill_ids: list[uuid.UUID] | None, **fields) -> Job:
    for key, value in fields.items():
        if value is not None:
            setattr(job, key, value)
    if skill_ids is not None:
        db.query(JobSkill).filter(JobSkill.job_id == job.id).delete()
        for skill_id in set(skill_ids):
            db.add(JobSkill(job_id=job.id, skill_id=skill_id))
    db.commit()
    db.refresh(job)
    return job


def set_status(db: Session, job: Job, status: JobStatus) -> Job:
    job.status = status
    db.commit()
    db.refresh(job)
    return job
def get_all(db: Session) -> list[Job]:
    query = select(Job).where(Job.status == JobStatus.PUBLISHED).order_by(Job.created_at.desc())
    return db.execute(query).scalars().unique().all()
def list_for_client(
    db: Session, client_id: uuid.UUID, offset: int, limit: int
) -> tuple[list[Job], int]:
    query = select(Job).where(Job.client_id == client_id)

    count_query = select(func.count()).select_from(query.with_only_columns(Job.id).subquery())
    total = db.execute(count_query).scalar_one()

    query = query.order_by(Job.created_at.desc()).offset(offset).limit(limit)
    items = db.execute(query).scalars().unique().all()
    return list(items), total


def search(
    db: Session,
    *,
    keyword: str | None,
    skill_id: uuid.UUID | None,status: JobStatus | None,min_budget: float | None,max_budget: float | None,sort_by: str,sort_dir: str,offset: int,limit: int,) -> tuple[list[Job], int]:
    query = select(Job)

    if keyword:
        like = f"%{keyword}%"
        query = query.where(Job.title.ilike(like) | Job.description.ilike(like))
    if status is not None:
        query = query.where(Job.status == status)
    if min_budget is not None:
        query = query.where(Job.budget_max >= min_budget)
    if max_budget is not None:
        query = query.where(Job.budget_min <= max_budget)
    if skill_id is not None:
        query = query.join(JobSkill, JobSkill.job_id == Job.id).where(JobSkill.skill_id == skill_id)

    count_query = select(func.count()).select_from(query.with_only_columns(Job.id).subquery())
    total = db.execute(count_query).scalar_one()

    sort_column = {"created_at": Job.created_at, "budget_min": Job.budget_min, "budget_max": Job.budget_max}.get(
        sort_by, Job.created_at
    )
    sort_column = sort_column.desc() if sort_dir == "desc" else sort_column.asc()

    query = query.order_by(sort_column).offset(offset).limit(limit)
    items = db.execute(query).scalars().unique().all()
    return list(items), total