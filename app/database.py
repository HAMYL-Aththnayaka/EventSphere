
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = (
    "postgresql+psycopg2://neondb_owner:npg_pax6z4BQGLFM"
    "@ep-muddy-pond-azwkle5m-pooler.c-3.ap-southeast-1.aws.neon.tech"
    "/neondb?sslmode=require&channel_binding=require"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
# =====================================================
# DATABASE SESSION DEPENDENCY
# =====================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =====================================================
# DATABASE INITIALIZATION
# =====================================================

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
