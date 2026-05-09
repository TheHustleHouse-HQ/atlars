import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def settings_override(monkeypatch):
    monkeypatch.setattr(settings, "env", "test")
    monkeypatch.setattr(settings, "mongo_db_name", "atlars_test")
    monkeypatch.setattr(settings, "redis_url", "redis://localhost:6379/15")
    yield

