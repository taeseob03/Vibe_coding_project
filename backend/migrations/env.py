from alembic import context
from app.accounts.models import User  # noqa: F401
from app.characters.effect_models import CharacterEffect, EffectGrant  # noqa: F401
from app.characters.models import Character  # noqa: F401
from app.core.config import get_settings
from app.core.db import Base
from app.integrations.models import ActivityRecord  # noqa: F401
from app.records.models import Record  # noqa: F401
from sqlalchemy import create_engine, pool

url = get_settings().database_url
if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=Base.metadata, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()
