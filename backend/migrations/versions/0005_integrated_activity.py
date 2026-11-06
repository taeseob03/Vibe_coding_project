"""User-owned B inputs/results and persisted character stats."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("characters", sa.Column("stats", sa.JSON(), nullable=True))
    op.create_table(
        "activity_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=True),
        sa.Column("image_mime", sa.String(30), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("analysis_data", sa.JSON(), nullable=True),
        sa.Column("analysis_error", sa.JSON(), nullable=True),
        sa.Column("stat_status", sa.String(20), nullable=False),
        sa.Column("state_error", sa.JSON(), nullable=True),
        sa.Column("category", sa.String(20), nullable=True),
        sa.Column("stats_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "request_id", name="uq_activity_request"),
    )
    op.create_index("ix_activity_records_user_id", "activity_records", ["user_id"])


def downgrade():
    op.drop_index("ix_activity_records_user_id", table_name="activity_records")
    op.drop_table("activity_records")
    with op.batch_alter_table("characters") as batch_op:
        batch_op.drop_column("stats")
