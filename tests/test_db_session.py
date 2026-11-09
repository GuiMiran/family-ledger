"""Engine/session boundaries: no server needed for URL inspection."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

from app.infrastructure.db.session import create_db_engine, create_session_factory


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+asyncpg", "postgresql+psycopg"])
def test_postgresql_urls_use_sync_driver_without_connecting(scheme):
    # create_engine loads a driver but must not contact this invalid host.
    engine = create_db_engine(
        f"{scheme}://ledger:p%40ss%3Aword@invalid.example:5432/family_ledger?sslmode=require"
    )
    try:
        assert engine.url.drivername == "postgresql+psycopg"
        assert engine.url.password == "p@ss:word"
        assert engine.url.query["sslmode"] == "require"
    finally:
        engine.dispose()


@pytest.mark.parametrize("url", ["sqlite://", "sqlite:///:memory:", "sqlite+pysqlite:///:memory:"])
def test_memory_database_survives_sessions_and_thread_handoff(url):
    engine = create_db_engine(url)
    factory = create_session_factory(engine)
    try:
        assert isinstance(engine.pool, StaticPool)
        with factory.begin() as session:
            assert session.expire_on_commit is False
            session.execute(text("CREATE TABLE values_seen (value INTEGER NOT NULL)"))
            session.execute(text("INSERT INTO values_seen VALUES (42)"))

        def read_in_other_thread():
            with factory() as session:
                return session.execute(text("SELECT value FROM values_seen")).scalar_one()

        with ThreadPoolExecutor(max_workers=1) as executor:
            assert executor.submit(read_in_other_thread).result() == 42
    finally:
        engine.dispose()


def test_sqlite_enforces_foreign_keys():
    engine = create_db_engine("sqlite://")
    factory = create_session_factory(engine)
    try:
        with engine.begin() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
            connection.execute(text("CREATE TABLE parents (id INTEGER PRIMARY KEY)"))
            connection.execute(text("CREATE TABLE children (parent_id INTEGER REFERENCES parents(id))"))
        with pytest.raises(IntegrityError):
            with factory.begin() as session:
                session.execute(text("INSERT INTO children VALUES (999)"))
        with factory() as session:
            assert session.execute(text("SELECT COUNT(*) FROM children")).scalar_one() == 0
    finally:
        engine.dispose()


def test_file_database_is_lazy_and_survives_engine_recreation(tmp_path):
    path = tmp_path / "durable.db"
    url = "sqlite:///" + str(path)
    engine = create_db_engine(url)
    assert not path.exists(), "Engine construction must not create/connect the database"
    with create_session_factory(engine).begin() as session:
        session.execute(text("CREATE TABLE durable (value TEXT NOT NULL)"))
        session.execute(text("INSERT INTO durable VALUES ('kept')"))
    engine.dispose()

    reopened = create_db_engine(url)
    try:
        with create_session_factory(reopened)() as session:
            assert session.execute(text("SELECT value FROM durable")).scalar_one() == "kept"
            assert session.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
    finally:
        reopened.dispose()


def test_async_sqlite_driver_is_rejected():
    with pytest.raises(ValueError, match="synchronous"):
        create_db_engine("sqlite+aiosqlite:///:memory:")
