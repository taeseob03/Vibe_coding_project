"""Onboarding drafts and one character per account."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("nickname", sa.String(12), nullable=True))
        batch_op.add_column(sa.Column("draft_color", sa.String(20), nullable=True))
        batch_op.add_column(
            sa.Column("setup_step", sa.String(20), nullable=False, server_default="nickname")
        )
        batch_op.add_column(
            sa.Column(
                "onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
    op.create_table(
        "characters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("color", sa.String(20), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_characters_user_id"),
    )


def downgrade():
    op.drop_table("characters")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("onboarding_completed")
        batch_op.drop_column("setup_step")
        batch_op.drop_column("draft_color")
        batch_op.drop_column("nickname")
