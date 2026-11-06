from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from sqlalchemy import create_engine, text


def test_id_login_migration_preserves_existing_records(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    engine = create_engine(url)
    try:
        command.upgrade(config, "0001")
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO users (id) VALUES ('legacy-user')"))
            connection.execute(
                text("""
                INSERT INTO records
                (id, user_id, text, status, analysis, effect_status, created_at)
                VALUES ('legacy-record', 'legacy-user', '기존 기록', 'pending', null,
                        'not_requested', '2026-11-06 10:00:00')
            """)
            )
        command.upgrade(config, "head")
        command.check(config)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT username FROM users")).scalar() is None
            assert connection.execute(text("SELECT text FROM records")).scalar() == "기존 기록"
        command.downgrade(config, "0001")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT user_id FROM records")).scalar() == "legacy-user"
        command.upgrade(config, "head")
        command.check(config)
    finally:
        engine.dispose()
        get_settings.cache_clear()
