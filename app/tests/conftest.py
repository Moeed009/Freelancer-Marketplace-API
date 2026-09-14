import uuid
from collections.abc import Iterator

import pytest
from fastapi import Depends, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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