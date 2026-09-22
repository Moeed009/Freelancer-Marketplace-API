from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.analytics import (
    AnalyticsTrendsResponse,
    ClientDashboard,
    ContractAnalytics,
    FreelancerDashboard,
    PerformanceAnalytics,
    SkillAnalyticsResponse,
)
from app.services.analytics_service import AnalyticsService


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get(
    "/dashboard",
    response_model=ClientDashboard | FreelancerDashboard,
)
def dashboard(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return AnalyticsService.get_dashboard(
            db,
            current_user,
            from_date,
            to_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.get(
    "/performance",
    response_model=PerformanceAnalytics,
)
def performance(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return AnalyticsService.get_performance(
            db,
            current_user,
            from_date,
            to_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.get(
    "/trends",
    response_model=AnalyticsTrendsResponse,
)
def trends(
    from_date: date,
    to_date: date,
    period: str = Query("month"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return AnalyticsService.get_trends(
            db,
            current_user,
            from_date,
            to_date,
            period,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.get(
    "/contracts",
    response_model=ContractAnalytics,
)
def contracts(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return AnalyticsService.get_contracts(
            db,
            current_user,
            from_date,
            to_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.get(
    "/skills",
    response_model=SkillAnalyticsResponse,
)
def skills(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return AnalyticsService.get_skills(
            db,
            current_user,
            from_date,
            to_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )