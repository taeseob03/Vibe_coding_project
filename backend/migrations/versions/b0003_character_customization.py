"""Persist character customization and onboarding drafts without resetting accounts."""

import sqlalchemy as sa
from alembic import op

revision = "b0003"
down_revision = "b0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("character_setup", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_column("character_setup")
