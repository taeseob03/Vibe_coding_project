"""Persist posts and mutually accepted friendships without changing A's character schema."""

import sqlalchemy as sa
from alembic import op

revision = "b0001"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "web_posts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=True),
        sa.Column("image_mime", sa.String(30), nullable=True),
        sa.Column("analysis_status", sa.String(20), nullable=False),
        sa.Column("analysis_data", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "request_id", name="uq_web_post_request"),
    )
    op.create_index("ix_web_posts_user_id", "web_posts", ["user_id"])
    op.create_index("ix_web_posts_created_at", "web_posts", ["created_at"])
    op.create_table(
        "web_friend_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_low", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("user_high", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requester_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_low", "user_high", name="uq_web_friend_pair"),
    )
    op.create_index("ix_web_friend_requests_user_low", "web_friend_requests", ["user_low"])
    op.create_index("ix_web_friend_requests_user_high", "web_friend_requests", ["user_high"])


def downgrade():
    op.drop_index("ix_web_friend_requests_user_high", table_name="web_friend_requests")
    op.drop_index("ix_web_friend_requests_user_low", table_name="web_friend_requests")
    op.drop_table("web_friend_requests")
    op.drop_index("ix_web_posts_created_at", table_name="web_posts")
    op.drop_index("ix_web_posts_user_id", table_name="web_posts")
    op.drop_table("web_posts")
