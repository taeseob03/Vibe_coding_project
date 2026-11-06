import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.db import get_engine
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEV_AUTH_ENABLED", "true")
    monkeypatch.setenv("LOCAL_WEB_PREVIEW_ENABLED", "false")
    monkeypatch.setenv("DEV_USER_ID", "00000000-0000-4000-8000-000000000001")
    get_settings.cache_clear()
    get_engine.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    from app.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    get_engine().dispose()
    get_engine.cache_clear()
    get_settings.cache_clear()


@pytest.fixture
def web_client(client, monkeypatch):
    monkeypatch.setenv("DEV_AUTH_ENABLED", "false")
    monkeypatch.setenv("LOCAL_WEB_PREVIEW_ENABLED", "true")
    get_settings.cache_clear()
    from app.main import create_app

    with TestClient(create_app()) as preview:
        yield preview
