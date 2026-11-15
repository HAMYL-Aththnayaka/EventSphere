
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker


load_dotenv()


def _normalize_database_url(database_url):
    if database_url.startswith("postgres://"):
        return database_url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1
        )
    if database_url.startswith("postgresql://"):
        return database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1
        )
    return database_url


def _database_url_from_environment():
    app_env = os.getenv("APP_ENV", "development").lower()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        if app_env == "production":
            raise RuntimeError(
                "DATABASE_URL must be configured with a PostgreSQL connection "
                "URL in production."
            )
        return "sqlite:///./eventsphere.db"

    database_url = _normalize_database_url(database_url)
    if app_env == "production" and not database_url.startswith(
        "postgresql+psycopg://"
    ):
        raise RuntimeError(
            "Production requires DATABASE_URL to use PostgreSQL."
        )
    return database_url


DATABASE_URL = _database_url_from_environment()

connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


# Database session dependency
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def initialize_database():
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    if "bookings" in inspector.get_table_names():
        columns = {
            column["name"]
            for column in inspector.get_columns("bookings")
        }

        if "refund_amount" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE bookings "
                        "ADD COLUMN refund_amount FLOAT NOT NULL DEFAULT 0"
                    )
                )
