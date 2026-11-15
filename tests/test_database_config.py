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


def test_database_url_must_be_configured_outside_production(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("APP_ENV", "development")

    with pytest.raises(RuntimeError, match="DATABASE_URL must be configured"):
        _database_url_from_environment()


def test_development_uses_configured_database_url(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./local.db")

    assert _database_url_from_environment() == "sqlite:///./local.db"


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
