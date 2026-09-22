

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "87e48bd5713e"
down_revision: Union[str, Sequence[str], None] = "1b22793431d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "file_attachments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column(
            "resource_type",
            sa.dialects.postgresql.ENUM(
                "PROFILE",
                "JOB",
                "PROPOSAL",
                "CONTRACT",
                "MILESTONE",
                name="file_resource_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("resource_id", sa.UUID(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.dialects.postgresql.ENUM(
                "PENDING",
                "CONFIRMED",
                name="file_attachment_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )

    op.create_index(
        "ix_file_attachments_owner_id",
        "file_attachments",
        ["owner_id"],
        unique=False,
    )

    op.create_index(
        "ix_file_attachments_resource",
        "file_attachments",
        ["resource_type", "resource_id"],
        unique=False,
    )

    op.create_index(
        "ix_file_attachments_status",
        "file_attachments",
        ["status"],
        unique=False,
    )

    op.drop_column("users", "phone")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "phone",
            sa.VARCHAR(length=20),
            autoincrement=False,
            nullable=True,
        ),
    )

    op.drop_index(
        "ix_file_attachments_status",
        table_name="file_attachments",
    )

    op.drop_index(
        "ix_file_attachments_resource",
        table_name="file_attachments",
    )

    op.drop_index(
        "ix_file_attachments_owner_id",
        table_name="file_attachments",
    )

    op.drop_table("file_attachments")