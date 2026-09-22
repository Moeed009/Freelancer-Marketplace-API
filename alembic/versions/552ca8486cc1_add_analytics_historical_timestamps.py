"""add analytics historical timestamps

Revision ID: 552ca8486cc1
Revises: 87e48bd5713e
Create Date: 2026-09-18 10:28:42.022489

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "552ca8486cc1"
down_revision: Union[str, Sequence[str], None] = "87e48bd5713e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "closed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "proposals",
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "proposals",
        sa.Column(
            "rejected_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "milestones",
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "milestones",
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "milestones",
        sa.Column(
            "rejected_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("milestones", "rejected_at")
    op.drop_column("milestones", "approved_at")
    op.drop_column("milestones", "submitted_at")

    op.drop_column("proposals", "rejected_at")
    op.drop_column("proposals", "accepted_at")

    op.drop_column("jobs", "closed_at")
    op.drop_column("jobs", "published_at")