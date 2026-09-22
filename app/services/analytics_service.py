from datetime import date

from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.services import notification_service
from app.repositories.analytics_repository import AnalyticsRepository


class AnalyticsService:

    @staticmethod
    def _validate_dates(
        from_date: date | None,
        to_date: date | None,
    ):
        if from_date and to_date and from_date > to_date:
            raise ValueError("from_date must be before or equal to to_date")

    @staticmethod
    def _validate_period(period: str):
        if period not in {"day", "week", "month"}:
            raise ValueError("period must be day, week, or month")

    @staticmethod
    def get_dashboard(
        db: Session,
        current_user,
        from_date: date | None = None,
        to_date: date | None = None,
    ):
        AnalyticsService._validate_dates(from_date, to_date)

        if current_user.role == UserRole.CLIENT:
            return AnalyticsRepository.get_client_dashboard(
                db,
                current_user.id,
                from_date,
                to_date,
            )

        return AnalyticsRepository.get_freelancer_dashboard(
            db,
            current_user.id,
            from_date,
            to_date,
        )

    @staticmethod
    def get_performance(
        db: Session,
        current_user,
        from_date: date | None = None,
        to_date: date | None = None,
    ):
        AnalyticsService._validate_dates(from_date, to_date)

        if current_user.role == UserRole.CLIENT:
            return AnalyticsRepository.get_client_performance(
                db,
                current_user.id,
                from_date,
                to_date,
            )

        return AnalyticsRepository.get_freelancer_performance(
            db,
            current_user.id,
            from_date,
            to_date,
        )

    @staticmethod
    def get_trends(
        db: Session,
        current_user,
        from_date: date,
        to_date: date,
        period: str,
    ):
        AnalyticsService._validate_dates(from_date, to_date)
        AnalyticsService._validate_period(period)

        if current_user.role == UserRole.CLIENT:
            data = AnalyticsRepository.get_client_trends(
                db,
                current_user.id,
                from_date,
                to_date,
                period,
            )
        else:
            data = AnalyticsRepository.get_freelancer_trends(
                db,
                current_user.id,
                from_date,
                to_date,
                period,
            )

        return {
            "period": period,
            "from_date": from_date,
            "to_date": to_date,
            "data": data,
        }

    @staticmethod
    def get_contracts(
        db: Session,
        current_user,
        from_date: date | None = None,
        to_date: date | None = None,
    ):
        AnalyticsService._validate_dates(from_date, to_date)

        if current_user.role == UserRole.CLIENT:
            return AnalyticsRepository.get_client_contracts(
                db,
                current_user.id,
                from_date,
                to_date,
            )

        return AnalyticsRepository.get_freelancer_contracts(
            db,
            current_user.id,
            from_date,
            to_date,
        )

    @staticmethod
    def get_skills(
        db: Session,
        current_user,
        from_date: date | None = None,
        to_date: date | None = None,
    ):
        AnalyticsService._validate_dates(from_date, to_date)

        return {
            "skills": AnalyticsRepository.get_skills(
                db,
                current_user.id,
                current_user.role.value,
                from_date,
                to_date,
            )
        }