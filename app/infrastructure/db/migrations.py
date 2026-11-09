"""Explicit, bounded 0.1 → 0.2 schema upgrade; never run at import/startup.

Only the known legacy/current schemas are accepted. Operators must stop writes,
back up and rehearse on a copy before invoking the upgrade on retained data.
"""
from __future__ import annotations

import uuid

from sqlalchemy import MetaData, func, inspect, select, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.schema import CreateTable

from app.infrastructure.db.orm import Base, Family, ProductAlias
from app.core.identity import ALIAS_QUARANTINE_FAMILY_ID, ALIAS_QUARANTINE_FAMILY_NAME

TEMP_ALIASES = "_product_aliases_v020"
NEW_TABLES = {"receipt_submissions", "receipt_events", "inventory_entries", "shopping_profiles", "price_observations", "shopping_audits"}
CORE_TABLES = set(Base.metadata.tables) - NEW_TABLES
LEGACY_UNIQUE = ["supermarket_id", "alias_text"]
SCOPED_UNIQUE = ["family_id", "product_id", "supermarket_id", "alias_text"]
# Reserved UUIDv5(URL, https://github.com/GuiMiran/family-ledger/alias-quarantine/v0.2).
# It is not an interactive household and cannot receive an admin-issued token.


class SchemaUpgradeError(ValueError):
    """The supplied schema cannot be upgraded safely by this bounded migration."""


def _schema_state(connection: Connection) -> str:
    inspector = inspect(connection)
    names = set(inspector.get_table_names())
    if TEMP_ALIASES in names:
        raise SchemaUpgradeError("Migration scratch table already exists; inspect it before retrying")
    known = names & set(Base.metadata.tables)
    if not known:
        return "empty"
    if not CORE_TABLES <= names:
        raise SchemaUpgradeError("Incomplete core schema; restore or review it before upgrading")
    alias_columns = {column["name"] for column in inspector.get_columns("product_aliases")}
    current_columns = set(ProductAlias.__table__.columns.keys())
    legacy_columns = current_columns - {"family_id"}
    unique = {constraint.get("name"): constraint["column_names"]
              for constraint in inspector.get_unique_constraints("product_aliases")}
    if (alias_columns == legacy_columns and unique.get("uq_alias_per_market") == LEGACY_UNIQUE
            and set(unique) == {"uq_alias_per_market"}):
        state = "legacy"
    elif (alias_columns == current_columns and unique.get("uq_alias_scoped") == SCOPED_UNIQUE
          and set(unique) == {"uq_alias_scoped"}):
        state = "current"
    else:
        raise SchemaUpgradeError("Unsupported alias columns or uniqueness; manual migration review required")
    for name in known - {"product_aliases"}:
        actual = {column["name"] for column in inspector.get_columns(name)}
        expected = set(Base.metadata.tables[name].columns.keys())
        if not expected <= actual:
            raise SchemaUpgradeError(f"Unsupported columns in {name}; manual migration review required")
    return state


def _require_supported_dialect(engine: Engine) -> None:
    if engine.dialect.name not in {"sqlite", "postgresql"}:
        raise SchemaUpgradeError("Only SQLite and PostgreSQL are supported by this migration")


def _begin_upgrade(connection: Connection) -> None:
    # pysqlite's legacy transaction mode does not BEGIN for DDL by itself.
    if connection.dialect.name == "sqlite":
        connection.exec_driver_sql("BEGIN IMMEDIATE")
    else:
        connection.begin()


def initialize_database(engine: Engine) -> dict:
    """Create an empty/current schema; explicitly reject legacy alias storage."""
    _require_supported_dialect(engine)
    with engine.connect() as connection:
        _begin_upgrade(connection)
        try:
            state = _schema_state(connection)
            if state == "legacy":
                raise SchemaUpgradeError("Legacy aliases detected; back up and run migrate-db explicitly")
            Base.metadata.create_all(connection)
            connection.commit()
            return {"status": "initialized" if state == "empty" else "current"}
        except BaseException:
            connection.rollback()
            raise


def _ensure_alias_quarantine(connection: Connection) -> None:
    row = connection.execute(select(Family.name).where(Family.id == ALIAS_QUARANTINE_FAMILY_ID)).first()
    if row is not None:
        if row.name != ALIAS_QUARANTINE_FAMILY_NAME:
            raise SchemaUpgradeError("Reserved quarantine family ID is occupied; owner review required")
        return
    connection.execute(Family.__table__.insert().values(
        id=ALIAS_QUARANTINE_FAMILY_ID, name=ALIAS_QUARANTINE_FAMILY_NAME, members_count=0
    ))


def _sqlite_upgrade_aliases(connection: Connection) -> None:
    inspector = inspect(connection)
    if inspector.get_pk_constraint("product_aliases")["constrained_columns"] != ["id"]:
        raise SchemaUpgradeError("Unsupported alias primary key; manual migration review required")
    expected_foreign_keys = {(("product_id",), "products", ("id",)),
                             (("supermarket_id",), "supermarkets", ("id",))}
    actual_foreign_keys = {(tuple(fk["constrained_columns"]), fk["referred_table"], tuple(fk["referred_columns"]))
                           for fk in inspector.get_foreign_keys("product_aliases")}
    if actual_foreign_keys != expected_foreign_keys:
        raise SchemaUpgradeError("Unsupported alias foreign keys; manual migration review required")
    checks = inspector.get_check_constraints("product_aliases")
    expected_check = "match_typein('exact','fuzzy','ai','manual')"
    if (len(checks) != 1 or "".join(checks[0]["sqltext"].lower().split()) != expected_check):
        raise SchemaUpgradeError("Unsupported alias check constraints; manual migration review required")
    indexes = inspector.get_indexes("product_aliases")
    if any(index["name"] != "ix_alias_text" for index in indexes):
        raise SchemaUpgradeError("Custom alias index found; manual migration review required")
    triggers = connection.execute(text(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='product_aliases'"
    )).all()
    if triggers:
        raise SchemaUpgradeError("Custom alias trigger found; manual migration review required")
    for name in inspector.get_table_names():
        for foreign_key in inspector.get_foreign_keys(name):
            if foreign_key.get("referred_table") == "product_aliases":
                raise SchemaUpgradeError("Inbound alias foreign key found; manual migration review required")

    metadata = MetaData()
    for name in ("families", "products", "supermarkets"):
        Base.metadata.tables[name].to_metadata(metadata)
    replacement = ProductAlias.__table__.to_metadata(metadata, name=TEMP_ALIASES)
    connection.execute(CreateTable(replacement))
    columns = list(ProductAlias.__table__.columns.keys())
    names = ", ".join('"' + name + '"' for name in columns)
    selection = ", ".join("COALESCE(products.family_id, :quarantine_id)" if name == "family_id" else f'aliases."{name}"'
                          for name in columns)
    connection.execute(text(
        f'INSERT INTO "{TEMP_ALIASES}" ({names}) '
        f'SELECT {selection} FROM product_aliases AS aliases '
        'JOIN products ON products.id = aliases.product_id'
    ), {"quarantine_id": str(ALIAS_QUARANTINE_FAMILY_ID)})
    before = connection.execute(text("SELECT COUNT(*) FROM product_aliases")).scalar_one()
    after = connection.execute(text(f'SELECT COUNT(*) FROM "{TEMP_ALIASES}"')).scalar_one()
    if before != after:
        raise SchemaUpgradeError("Alias row-count mismatch; migration aborted")
    missing = connection.execute(text(
        f'SELECT id FROM product_aliases EXCEPT SELECT id FROM "{TEMP_ALIASES}"'
    )).all()
    if missing:
        raise SchemaUpgradeError("Alias identifiers did not survive the migration")
    connection.exec_driver_sql("DROP TABLE product_aliases")
    connection.exec_driver_sql(f'ALTER TABLE "{TEMP_ALIASES}" RENAME TO product_aliases')
    for index in ProductAlias.__table__.indexes:
        index.create(connection)
    if connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
        raise SchemaUpgradeError("Foreign-key integrity check failed; migration aborted")


def _postgresql_upgrade_aliases(connection: Connection) -> None:
    connection.exec_driver_sql("LOCK TABLE product_aliases IN ACCESS EXCLUSIVE MODE")
    connection.exec_driver_sql(
        "ALTER TABLE product_aliases ADD COLUMN family_id UUID REFERENCES families(id)"
    )
    connection.execute(text(
        "UPDATE product_aliases AS aliases SET family_id = COALESCE(products.family_id, CAST(:quarantine_id AS UUID)) "
        "FROM products WHERE products.id = aliases.product_id"
    ), {"quarantine_id": str(ALIAS_QUARANTINE_FAMILY_ID)})
    connection.exec_driver_sql(
        "ALTER TABLE product_aliases DROP CONSTRAINT uq_alias_per_market"
    )
    connection.exec_driver_sql(
        "ALTER TABLE product_aliases ADD CONSTRAINT uq_alias_scoped "
        "UNIQUE (family_id, product_id, supermarket_id, alias_text)"
    )


def migrate_database(engine: Engine) -> dict:
    """Explicit transactional upgrade, retaining alias IDs and original rows.

    Legacy aliases of global products have unknown provenance and are isolated
    under a reserved non-login family until explicitly reviewed by an operator.
    """
    _require_supported_dialect(engine)
    with engine.connect() as connection:
        _begin_upgrade(connection)
        try:
            state = _schema_state(connection)
            old_count = 0
            if state == "legacy":
                old_count = connection.execute(text("SELECT COUNT(*) FROM product_aliases")).scalar_one()
                # Existing dangling product references cannot be assigned safely.
                invalid = connection.execute(text(
                    "SELECT aliases.id FROM product_aliases AS aliases LEFT JOIN products "
                    "ON products.id = aliases.product_id WHERE products.id IS NULL"
                )).first()
                if invalid:
                    raise SchemaUpgradeError("Dangling alias product reference; repair before migration")
                unknown_provenance = connection.execute(text(
                    "SELECT COUNT(*) FROM product_aliases AS aliases JOIN products "
                    "ON products.id = aliases.product_id WHERE products.family_id IS NULL"
                )).scalar_one()
                if unknown_provenance:
                    _ensure_alias_quarantine(connection)
                if connection.dialect.name == "sqlite":
                    _sqlite_upgrade_aliases(connection)
                else:
                    _postgresql_upgrade_aliases(connection)
                if connection.execute(text("SELECT COUNT(*) FROM product_aliases")).scalar_one() != old_count:
                    raise SchemaUpgradeError("Alias row-count mismatch; migration aborted")
            Base.metadata.create_all(connection)
            if _schema_state(connection) != "current":
                raise SchemaUpgradeError("Schema upgrade did not produce the supported current layout")
            quarantined = connection.execute(select(func.count()).select_from(ProductAlias).where(
                ProductAlias.family_id == ALIAS_QUARANTINE_FAMILY_ID
            )).scalar_one()
            connection.commit()
            return {"status": "migrated" if state == "legacy" else "initialized" if state == "empty" else "current",
                    "migrated_aliases": old_count,
                    "quarantined_aliases_requiring_owner_review": quarantined}
        except BaseException:
            connection.rollback()
            raise
