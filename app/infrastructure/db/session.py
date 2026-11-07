"""Synchronous SQLAlchemy configuration without import-time database effects.

Database schema initialization and upgrades belong to explicit application or
operator commands. Creating an engine here never creates tables or connects.
"""
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def create_db_engine(database_url: str) -> Engine:
    """Build a lazy sync engine for PostgreSQL/psycopg or SQLite.

    Hosted PostgreSQL connection strings often use postgres:// or asyncpg.
    Normalize those schemes through SQLAlchemy's URL object so escaped
    usernames/passwords and connection query parameters retain their meaning.
    """
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql", "postgresql+asyncpg"}:
        url = url.set(drivername="postgresql+psycopg")

    if url.get_backend_name() != "sqlite":
        return create_engine(url, pool_pre_ping=True)

    if url.drivername not in {"sqlite", "sqlite+pysqlite"}:
        raise ValueError("SQLite requires the synchronous pysqlite driver")

    options: dict = {"connect_args": {"check_same_thread": False}}
    memory = (
        url.database in {None, "", ":memory:"}
        or url.query.get("mode") == "memory"
        or bool(url.database and url.database.startswith("file::memory:"))
    )
    if memory:
        options["poolclass"] = StaticPool
    engine = create_engine(url, **options)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create independent synchronous sessions; callers own commit/rollback."""
    return sessionmaker(bind=engine, expire_on_commit=False)
