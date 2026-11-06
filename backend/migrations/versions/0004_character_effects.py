"""Effect inventory and idempotent per-record grants."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "character_effects",
        sa.Column("character_id", sa.String(36), sa.ForeignKey("characters.id"), primary_key=True),
        sa.Column("effect_id", sa.String(20), primary_key=True),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("visible", sa.Boolean(), nullable=False),
        sa.CheckConstraint("level >= 1", name="ck_character_effect_level"),
    )
    op.create_table(
        "effect_grants",
        sa.Column("record_id", sa.String(36), sa.ForeignKey("records.id"), primary_key=True),
        sa.Column("character_id", sa.String(36), sa.ForeignKey("characters.id"), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("effects_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_effect_grants_character_id", "effect_grants", ["character_id"])


def downgrade():
    op.drop_index("ix_effect_grants_character_id", table_name="effect_grants")
    op.drop_table("effect_grants")
    op.drop_table("character_effects")
