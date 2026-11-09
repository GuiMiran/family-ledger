"""Explicit SQLite legacy upgrade, rollback and offline provisioning boundaries."""
import json
import uuid
from datetime import datetime, timezone

import jwt
import pytest
from sqlalchemy import event, inspect, select, text

from app.admin import main
from app.core.auth import ISSUER, AUDIENCE
from app.infrastructure.db.migrations import (
    ALIAS_QUARANTINE_FAMILY_ID, ALIAS_QUARANTINE_FAMILY_NAME,
    initialize_database, migrate_database, SchemaUpgradeError, NEW_TABLES,
)
from app.infrastructure.db.orm import Base, Family, Product, ProductAlias, Supermarket
from app.infrastructure.db.session import create_db_engine
from app.infrastructure.normalization.matchers import ExactMatcher, FuzzyMatcher
from sqlalchemy.orm import Session


@pytest.fixture
def legacy(tmp_path):
    engine = create_db_engine("sqlite:///" + str(tmp_path / "legacy.db"))
    tables = [table for name, table in Base.metadata.tables.items()
              if name != "product_aliases" and name not in NEW_TABLES]
    Base.metadata.create_all(engine, tables=tables)
    family, private, shared, shop, private_alias, shared_alias = [uuid.uuid4() for _ in range(6)]
    now = datetime.now(timezone.utc).isoformat(sep=" ")
    with engine.begin() as connection:
        connection.exec_driver_sql("""CREATE TABLE product_aliases (
            id CHAR(36) PRIMARY KEY NOT NULL,
            product_id CHAR(36) NOT NULL REFERENCES products(id),
            supermarket_id CHAR(36) REFERENCES supermarkets(id),
            alias_text TEXT NOT NULL,
            match_type VARCHAR(8) NOT NULL CHECK (match_type IN ('exact','fuzzy','ai','manual')),
            confidence NUMERIC(4,3) NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            CONSTRAINT uq_alias_per_market UNIQUE (supermarket_id, alias_text)
        )""")
        connection.exec_driver_sql("CREATE INDEX ix_alias_text ON product_aliases(alias_text)")
        connection.execute(Family.__table__.insert(), {"id":family,"name":"Synthetic legacy family"})
        connection.execute(Supermarket.__table__.insert(), {"id":shop,"name":"Synthetic shop","parser_key":"makro"})
        connection.execute(Product.__table__.insert(), [
            {"id":private,"family_id":family,"canonical_name":"Private","default_unit":"unit"},
            {"id":shared,"family_id":None,"canonical_name":"Shared","default_unit":"unit"},
        ])
        for alias_id, product, label in [(private_alias,private,"PRIVATE"),(shared_alias,shared,"SHARED")]:
            connection.execute(text("""INSERT INTO product_aliases
                (id,product_id,supermarket_id,alias_text,match_type,confidence,created_at,updated_at)
                VALUES (:id,:product,:shop,:label,'manual',0.95,:now,:now)"""),
                {"id":str(alias_id),"product":str(product),"shop":str(shop),"label":label,"now":now})
    yield engine, {"family":family,"private":private,"shared":shared,"shop":shop,
                   "private_alias":private_alias,"shared_alias":shared_alias}
    engine.dispose()


def test_init_refuses_legacy_schema_without_changing_rows(legacy):
    engine, ids = legacy
    with pytest.raises(SchemaUpgradeError, match="migrate-db"):
        initialize_database(engine)
    assert "family_id" not in {c["name"] for c in inspect(engine).get_columns("product_aliases")}
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM product_aliases")).scalar_one() == 2


def test_migration_retains_ids_values_and_scopes_private_aliases(legacy):
    engine, ids = legacy
    with engine.connect() as connection:
        before = {row.id:dict(row._mapping) for row in connection.execute(text("SELECT * FROM product_aliases"))}
    result = migrate_database(engine)
    assert result == {"status":"migrated","migrated_aliases":2,"quarantined_aliases_requiring_owner_review":1}
    with engine.connect() as connection:
        after = {row.id:dict(row._mapping) for row in connection.execute(text("SELECT * FROM product_aliases"))}
        assert set(after) == set(before)
        for alias_id, row in before.items():
            for column, value in row.items():
                assert after[alias_id][column] == value
        assert after[str(ids["private_alias"])]["family_id"] == str(ids["family"])
        assert after[str(ids["shared_alias"])]["family_id"] == str(ALIAS_QUARANTINE_FAMILY_ID)
        assert connection.execute(select(Family.name).where(Family.id == ALIAS_QUARANTINE_FAMILY_ID)).scalar_one() == ALIAS_QUARANTINE_FAMILY_NAME
        assert not connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    constraints = {item["name"] for item in inspect(engine).get_unique_constraints("product_aliases")}
    assert constraints == {"uq_alias_scoped"}
    assert NEW_TABLES <= set(inspect(engine).get_table_names())
    assert "_product_aliases_v020" not in inspect(engine).get_table_names()
    assert initialize_database(engine)["status"] == "current"
    assert migrate_database(engine) == {"status":"current","migrated_aliases":0,"quarantined_aliases_requiring_owner_review":1}
    with Session(engine) as session:
        for matcher in (ExactMatcher(session), FuzzyMatcher(session)):
            assert matcher.match("SHARED", ids["shop"], ids["family"]) is None
            assert matcher.match("SHARED", ids["shop"], uuid.uuid4()) is None
            assert matcher.match("SHARED", ids["shop"], None) is None


def test_migration_rolls_back_alias_rebuild_and_table_creation(legacy):
    engine, ids = legacy
    with engine.connect() as connection:
        before = connection.execute(text("SELECT * FROM product_aliases ORDER BY id")).all()

    def fail_after_alias_rebuild(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith("CREATE TABLE receipt_"):
            raise RuntimeError("Synthetic upgrade failure")

    event.listen(engine, "before_cursor_execute", fail_after_alias_rebuild)
    try:
        with pytest.raises(RuntimeError, match="Synthetic upgrade failure"):
            migrate_database(engine)
    finally:
        event.remove(engine, "before_cursor_execute", fail_after_alias_rebuild)
    assert "family_id" not in {c["name"] for c in inspect(engine).get_columns("product_aliases")}
    assert not (NEW_TABLES & set(inspect(engine).get_table_names()))
    assert "_product_aliases_v020" not in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT * FROM product_aliases ORDER BY id")).all() == before
        assert connection.execute(select(Family.id).where(Family.id == ALIAS_QUARANTINE_FAMILY_ID)).first() is None


def test_no_quarantine_family_is_created_when_not_needed(legacy):
    engine, ids = legacy
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM product_aliases WHERE id=:id"), {"id":str(ids["shared_alias"])})
    result = migrate_database(engine)
    assert result["quarantined_aliases_requiring_owner_review"] == 0
    with engine.connect() as connection:
        assert connection.execute(select(Family.id).where(Family.id == ALIAS_QUARANTINE_FAMILY_ID)).first() is None


def test_reserved_family_id_collision_aborts_upgrade(legacy):
    engine, ids = legacy
    with engine.begin() as connection:
        connection.execute(Family.__table__.insert(), {"id":ALIAS_QUARANTINE_FAMILY_ID,"name":"Occupied by unrelated household"})
    with pytest.raises(SchemaUpgradeError, match="Reserved quarantine"):
        migrate_database(engine)
    assert "family_id" not in {c["name"] for c in inspect(engine).get_columns("product_aliases")}


def test_explicit_owner_review_can_release_only_approved_alias(legacy):
    engine, ids = legacy
    migrate_database(engine)
    # This is a deliberately explicit operator decision, not inferred provenance.
    with engine.begin() as connection:
        connection.execute(ProductAlias.__table__.update().where(
            ProductAlias.id == ids["shared_alias"]
        ).values(family_id=None))
    with Session(engine) as session:
        assert ExactMatcher(session).match("SHARED", ids["shop"], ids["family"]).product_id == ids["shared"]
    assert migrate_database(engine)["quarantined_aliases_requiring_owner_review"] == 0


def test_unknown_alias_columns_are_refused(legacy):
    engine, ids = legacy
    with engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE product_aliases ADD COLUMN custom_data TEXT")
    with pytest.raises(SchemaUpgradeError, match="Unsupported alias"):
        migrate_database(engine)
    assert "family_id" not in {c["name"] for c in inspect(engine).get_columns("product_aliases")}


def test_unknown_alias_trigger_is_refused(legacy):
    engine, ids = legacy
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TRIGGER preserve_me AFTER UPDATE ON product_aliases BEGIN SELECT 1; END")
    with pytest.raises(SchemaUpgradeError, match="trigger"):
        migrate_database(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT name FROM sqlite_master WHERE type='trigger'")).scalar_one() == "preserve_me"


def test_empty_database_init_and_migrate_are_explicit_and_idempotent(tmp_path):
    engine = create_db_engine("sqlite:///" + str(tmp_path / "empty.db"))
    try:
        assert initialize_database(engine)["status"] == "initialized"
        assert initialize_database(engine)["status"] == "current"
        assert migrate_database(engine)["status"] == "current"
    finally:
        engine.dispose()


def test_admin_provisions_existing_family_and_expiring_token(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "admin.db"))
    monkeypatch.setenv("JWT_SECRET", "synthetic-admin-test-secret-32chars-long")
    assert main(["init-db"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "initialized"
    assert main(["create-family","--name","Synthetic provisioned family"]) == 0
    family = uuid.UUID(capsys.readouterr().out.strip())
    assert main(["token","--family",str(family),"--hours","1"]) == 0
    token = capsys.readouterr().out.strip()
    claims = jwt.decode(token,"synthetic-admin-test-secret-32chars-long",algorithms=["HS256"],issuer=ISSUER,audience=AUDIENCE)
    assert claims["family_id"] == str(family)
    assert claims["exp"] - claims["iat"] == 3600


def test_admin_refuses_unprovisioned_family_and_weak_secret(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "admin.db"))
    assert main(["init-db"]) == 0
    capsys.readouterr()
    monkeypatch.setenv("JWT_SECRET", "weak")
    assert main(["token","--family",str(uuid.uuid4())]) == 1
    result = capsys.readouterr()
    assert result.out == "" and "32 characters" in result.err
    monkeypatch.setenv("JWT_SECRET", "synthetic-admin-test-secret-32chars-long")
    assert main(["token","--family",str(uuid.uuid4())]) == 1
    assert "not provisioned" in capsys.readouterr().err


def test_admin_lifetime_is_bounded_and_database_url_required(monkeypatch, capsys):
    with pytest.raises(SystemExit) as error:
        main(["token","--family",str(uuid.uuid4()),"--hours","25"])
    assert error.value.code == 2
    capsys.readouterr()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main(["init-db"]) == 1
    assert "DATABASE_URL is required" in capsys.readouterr().err


def test_admin_token_refuses_reserved_quarantine_family(legacy, monkeypatch, capsys):
    engine, ids = legacy
    migrate_database(engine)
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("JWT_SECRET", "synthetic-admin-test-secret-32chars-long")
    assert main(["token","--family",str(ALIAS_QUARANTINE_FAMILY_ID)]) == 1
    result = capsys.readouterr()
    assert result.out == "" and "quarantine family" in result.err
