import pytest

from app.database import (
    _database_url_from_environment,
    _normalize_database_url,
)


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        (
            "postgres://user:password@host/database",
            "postgresql+psycopg://user:password@host/database",
        ),
        (
            "postgresql://user:password@host/database",
            "postgresql+psycopg://user:password@host/database",
        ),
        (
            "postgresql+psycopg://user:password@host/database",
            "postgresql+psycopg://user:password@host/database",
        ),
    ],
)
def test_normalize_database_url(database_url, expected):
    assert _normalize_database_url(database_url) == expected


def test_database_url_defaults_to_sqlite_outside_production(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("APP_ENV", "development")

    assert _database_url_from_environment() == "sqlite:///./eventsphere.db"


@pytest.mark.parametrize(
    ("database_url", "error"),
    [
        (None, "DATABASE_URL must be configured"),
        ("sqlite:///./eventsphere.db", "Production requires DATABASE_URL"),
    ],
)
def test_production_requires_postgresql(monkeypatch, database_url, error):
    monkeypatch.setenv("APP_ENV", "production")
    if database_url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", database_url)

    with pytest.raises(RuntimeError, match=error):
        _database_url_from_environment()
