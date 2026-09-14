import uuid

from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import User


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create(db: Session, *, user_id: uuid.UUID, email: str, role: UserRole, full_name: str | None) -> User:
    user = User(id=user_id, email=email, role=role, full_name=full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_profile_fields(db: Session, user: User, *, full_name: str | None) -> User:
    if full_name is not None:
        user.full_name = full_name
    db.commit()
    db.refresh(user)
    return user


def delete(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()

def set_avatar(db: Session, user: User, avatar_url: str) -> User:
    user.avatar_url = avatar_url
    db.commit()
    db.refresh(user)
    return user