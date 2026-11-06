"""Ordered B stat events, titles and authenticated lounges."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("characters") as batch:
        batch.add_column(
            sa.Column("stat_revision", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("title_id", sa.String(40), nullable=True))
    with op.batch_alter_table("activity_records") as batch:
        batch.add_column(
            sa.Column("source", sa.String(20), nullable=False, server_default="gemini")
        )
        batch.add_column(sa.Column("applied_order", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("stack_changes", sa.JSON(), nullable=True))
        batch.create_unique_constraint("uq_activity_order", ["user_id", "applied_order"])
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, user_id FROM activity_records "
            "WHERE stat_status='applied' ORDER BY created_at, id"
        )
    ).all()
    counters = {}
    for record_id, user_id in rows:
        counters[user_id] = counters.get(user_id, 0) + 1
        connection.execute(
            sa.text("UPDATE activity_records SET applied_order=:n WHERE id=:id"),
            {"n": counters[user_id], "id": record_id},
        )
    for user_id, count in counters.items():
        connection.execute(
            sa.text("UPDATE characters SET stat_revision=:n WHERE user_id=:u"),
            {"n": count, "u": user_id},
        )
    op.create_table(
        "character_titles",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("title_id", sa.String(40), primary_key=True),
    )
    op.create_table(
        "lounges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.UniqueConstraint("owner_id"),
    )
    op.create_table(
        "lounge_members",
        sa.Column("room_id", sa.String(36), sa.ForeignKey("lounges.id"), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
    )
    op.create_table(
        "lounge_invitations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("room_id", sa.String(36), sa.ForeignKey("lounges.id"), nullable=False),
        sa.Column("sender_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recipient_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.UniqueConstraint("room_id", "recipient_id", name="uq_lounge_recipient"),
    )
    op.create_index("ix_lounge_invitations_room_id", "lounge_invitations", ["room_id"])
    op.create_index("ix_lounge_invitations_recipient_id", "lounge_invitations", ["recipient_id"])


def downgrade():
    op.drop_index("ix_lounge_invitations_recipient_id", table_name="lounge_invitations")
    op.drop_index("ix_lounge_invitations_room_id", table_name="lounge_invitations")
    for table in ["lounge_invitations", "lounge_members", "lounges", "character_titles"]:
        op.drop_table(table)
    with op.batch_alter_table("activity_records") as batch:
        batch.drop_constraint("uq_activity_order", type_="unique")
        for name in ["stack_changes", "applied_order", "source"]:
            batch.drop_column(name)
    with op.batch_alter_table("characters") as batch:
        batch.drop_column("title_id")
        batch.drop_column("stat_revision")
