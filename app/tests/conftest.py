import uuid
from collections.abc import Iterator

import pytest
from fastapi import Depends, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.database as database_module
from app.core.exceptions import UnauthorizedError
from app.db.base import Base
from app.db.database import get_db
from app.dependencies.auth import (
    get_current_user,
    get_current_user_optional,
)
from app.main import app
from app.models.enums import UserRole
from app.models.user import User


TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# session_scope() (used by notification_service.emit() and the dispatcher)
# opens its own sessions from app.db.database.SessionLocal directly - it is
# NOT reached by app.dependency_overrides, which only affects FastAPI's
# Depends(get_db). Without this line, emit() keeps talking to the real
# settings.DATABASE_URL engine instead of this test database, so any user
# created via the `db` fixture is invisible to it ("recipient not found").
database_module.SessionLocal = TestingSessionLocal


def _override_get_db() -> Iterator[Session]:
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _fresh_db() -> Iterator[None]:
    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(_fresh_db: None) -> Iterator[Session]:
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()


def _make_user(
    db_session: Session,
    role: UserRole,
    email: str,
) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        role=role,
        full_name=email.split("@")[0],
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture
def client_user(db: Session) -> User:
    return _make_user(
        db,
        UserRole.CLIENT,
        "client@test.com",
    )


@pytest.fixture
def other_client_user(db: Session) -> User:
    return _make_user(
        db,
        UserRole.CLIENT,
        "other-client@test.com",
    )


@pytest.fixture
def freelancer_user(db: Session) -> User:
    return _make_user(
        db,
        UserRole.FREELANCER,
        "freelancer@test.com",
    )


@pytest.fixture
def other_freelancer_user(db: Session) -> User:
    return _make_user(
        db,
        UserRole.FREELANCER,
        "other-freelancer@test.com",
    )


@pytest.fixture
def as_user():
    def _resolve_current_user(
        request: Request,
        db: Session = Depends(get_db),
    ) -> User:
        user_id = request.headers.get("X-Test-User-Id")

        if not user_id:
            raise UnauthorizedError("Missing bearer token.")

        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise UnauthorizedError("Invalid test user ID.")

        user = db.get(User, user_uuid)

        if user is None:
            raise UnauthorizedError("User not found.")

        return user

    def _resolve_current_user_optional(
        request: Request,
        db: Session = Depends(get_db),
    ) -> User | None:
        user_id = request.headers.get("X-Test-User-Id")

        if not user_id:
            return None

        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            return None

        return db.get(User, user_uuid)

    app.dependency_overrides[get_current_user] = _resolve_current_user
    app.dependency_overrides[get_current_user_optional] = (
        _resolve_current_user_optional
    )

    def _make(user: User) -> TestClient:
        test_client = TestClient(app)
        test_client.headers.update(
            {
                "X-Test-User-Id": str(user.id),
            }
        )
        return test_client

    yield _make

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_user_optional, None)


@pytest.fixture
def anon_client() -> Iterator[TestClient]:
    return TestClient(app)


@pytest.fixture
def email_provider():
    """Fake EMAIL provider double for notification tests.

    Swapped in for the real provider via app.notifications.providers'
    registry (set_provider/reset_providers) so notification_service /
    notification_dispatcher never make a real network call in tests.

    - .sent      -> list of (destination, message) actually "delivered"
    - .calls     -> total number of send() attempts (sent + failed)
    - .script    -> optional queue of exceptions to raise instead of
                    succeeding, one per call, in order (e.g. set this to
                    [providers.TransientProviderError("...")] to simulate
                    a failure on the next send()).
    """
    from app.models.enums import NotificationChannel
    from app.notifications import providers

    class FakeEmailProvider:
        channel = NotificationChannel.EMAIL

        def __init__(self):
            self.sent: list[tuple[str, object]] = []
            self.calls = 0
            self.script: list[Exception] = []

        def send(self, destination: str, message) -> None:
            self.calls += 1
            if self.script:
                raise self.script.pop(0)
            self.sent.append((destination, message))

    fake = FakeEmailProvider()
    providers.set_provider(NotificationChannel.EMAIL, fake)

    yield fake

    providers.reset_providers()