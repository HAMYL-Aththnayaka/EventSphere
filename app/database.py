
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker


# Use PostgreSQL when DATABASE_URL is configured.
# Otherwise, use SQLite for local development.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./eventsphere.db"
)

# Use the psycopg 3 driver included in requirements.txt.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+psycopg://",
        1
    )
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )


# SQLitespecial connection argument.
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
