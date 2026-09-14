import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FreelancerSkill(Base):
   
    __tablename__ = "freelancer_skills"
    __table_args__ = (
        UniqueConstraint("freelancer_profile_id", "skill_id", name="uq_freelancer_skill"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    freelancer_profile_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("freelancer_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )

    freelancer_profile = relationship("FreelancerProfile", back_populates="freelancer_skills")
    skill = relationship("Skill", back_populates="freelancer_skills")
