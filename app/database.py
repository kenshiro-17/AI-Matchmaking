import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker


def _default_database_url() -> str:
    if os.getenv("VERCEL") == "1":
        # Vercel filesystem is ephemeral; /tmp is writable during invocation lifecycle.
        return "sqlite:////tmp/matchmaking.db"
    return "sqlite:///./matchmaking.db"


DATABASE_URL = os.getenv("DATABASE_URL", _default_database_url())

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()


def ensure_schema_compat():
    """Best-effort SQLite schema compatibility for additive columns."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    with engine.begin() as conn:
        cols = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(attendees)").fetchall()
        }
        if "linkedin_opt_in" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE attendees ADD COLUMN linkedin_opt_in INTEGER NOT NULL DEFAULT 0"
            )
        if "linkedin_url" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE attendees ADD COLUMN linkedin_url VARCHAR(280) NOT NULL DEFAULT ''"
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
