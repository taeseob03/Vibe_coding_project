"""C pixel character appearance and university profile."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("grade", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(
            sa.Column("major", sa.String(20), nullable=False, server_default="computer")
        )
        batch.add_column(sa.Column("draft_appearance", sa.JSON(), nullable=True))
    op.add_column("characters", sa.Column("appearance", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("characters") as batch:
        batch.drop_column("appearance")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("draft_appearance")
        batch.drop_column("major")
        batch.drop_column("grade")
