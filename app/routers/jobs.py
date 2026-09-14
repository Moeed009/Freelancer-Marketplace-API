import math
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.db.database import get_db
from app.dependencies.auth import get_current_user_optional, require_client
from app.dependencies.pagination import PaginationParams
from app.models.enums import JobStatus
from app.models.job import Job
from app.models.user import User
from app.schemas.common import Page
from app.schemas.job import JobCreateRequest, JobOut, JobStatusUpdateRequest, JobUpdateRequest
from app.services import job_service

router = APIRouter(prefix="", tags=["Jobs"])


def _serialize(job: Job) -> JobOut:
    out = JobOut.model_validate(job)
    out.skills = [js.skill for js in job.job_skills]
    return out


@router.post("/Create_job", response_model=JobOut, status_code=status.HTTP_201_CREATED, summary="Create a job posting (CLIENT only)")
def create_job(payload: JobCreateRequest, client: User = Depends(require_client), db: Session = Depends(get_db)):
    job = job_service.create_job(db, client, payload)
    return _serialize(job)


@router.get(
    "/Search_job",
    response_model=Page[JobOut],
    summary="Search/browse published jobs (public), or pass mine=true to list jobs you posted (CLIENT only, any status)",
)
def search_jobs(
    mine: bool = Query(default=False, description="If true, returns jobs posted by the caller (any status)"),
    keyword: str | None = Query(default=None, description="Matches against title/description"),
    skill_id: uuid.UUID | None = Query(default=None),
    status_filter: JobStatus | None = Query(default=JobStatus.PUBLISHED, alias="status"),
    min_budget: float | None = Query(default=None, ge=0),
    max_budget: float | None = Query(default=None, ge=0),
    sort_by: str = Query(default="created_at", pattern="^(created_at|budget_min|budget_max)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    pagination: PaginationParams = Depends(),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if mine:
        if current_user is None:
            raise UnauthorizedError("Login required to list your own jobs.")
        if current_user.role.value != "CLIENT":
            raise ForbiddenError("Only clients have posted jobs to list.")
        items, total = job_service.list_my_jobs(
            db, current_user, offset=pagination.offset, limit=pagination.page_size
        )
    else:
        items, total = job_service.search_jobs(
            db,
            keyword=keyword,
            skill_id=skill_id,
            status=status_filter,
            min_budget=min_budget,
            max_budget=max_budget,
            sort_by=sort_by,
            sort_dir=sort_dir,
            offset=pagination.offset,
            limit=pagination.page_size,
        )

    return Page(
        items=[_serialize(j) for j in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=math.ceil(total / pagination.page_size) if total else 0,
    )


@router.patch("/Update_job", response_model=JobOut, summary="Update a job you own(CLIENT only)")
def update_job(
    job_id: uuid.UUID,
    payload: JobUpdateRequest,
    client: User = Depends(require_client),
    db: Session = Depends(get_db),
):
    job = job_service.update_job(db, client, job_id, payload)
    return _serialize(job)


@router.patch("/job_status", response_model=JobOut, summary="Publish or close a job you own(CLIENT only)")
def change_job_status(
    job_id: uuid.UUID,
    payload: JobStatusUpdateRequest,
    client: User = Depends(require_client),
    db: Session = Depends(get_db),
):
    job = job_service.change_status(db, client, job_id, payload.status)
    return _serialize(job)


@router.delete(
    "/Delete_job",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a DRAFT job you own, before it has any proposals (CLIENT only)",
)
def delete_job(job_id: uuid.UUID, client: User = Depends(require_client), db: Session = Depends(get_db)):
    job_service.delete_job(db, client, job_id)