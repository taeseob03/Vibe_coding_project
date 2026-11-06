"""ID-only account access and persistent sessions."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("username", sa.String(20), nullable=True))
        batch_op.create_unique_constraint("uq_users_username", ["username"])
    op.create_table(
        "login_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_login_sessions_user_id", "login_sessions", ["user_id"])
    op.create_index("ix_login_sessions_expires_at", "login_sessions", ["expires_at"])


def downgrade():
    op.drop_index("ix_login_sessions_expires_at", table_name="login_sessions")
    op.drop_index("ix_login_sessions_user_id", table_name="login_sessions")
    op.drop_table("login_sessions")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_username", type_="unique")
        batch_op.drop_column("username")
