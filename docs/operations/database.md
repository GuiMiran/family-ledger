# Database and deployment configuration

Family Ledger 0.2.0 uses synchronous SQLAlchemy sessions. Install the declared
application dependencies with `python -m pip install -e ".[dev]"`. The package
includes `app*` only; documentation and the UI prototype are not Python packages.
PostgreSQL uses `psycopg` 3, including its binary distribution. PostgreSQL URLs
with `postgres://`, `postgresql://` or `postgresql+asyncpg://` are normalized to
`postgresql+psycopg://`; no async session or asyncpg driver is used.

`create_db_engine(database_url)` creates a lazy engine without connecting or
creating tables. `create_session_factory(engine)` creates synchronous sessions
with `expire_on_commit=False`; its callers own commit/rollback and closure.
Application schema initialization is an explicit action, never an import side
effect. Do not use table creation as a substitute for an existing-schema upgrade.

## Explicit offline administration

All commands read `DATABASE_URL`. Run them from a trusted operator shell, not
through a public HTTP endpoint:

```sh
python -m app.admin init-db
python -m app.admin create-family --name "Example family"
python -m app.admin token --family FAMILY_UUID --hours 1
```

`init-db` creates an empty/current schema and refuses the legacy alias layout;
it does not silently upgrade retained data. `create-family` prints its new UUID.
Replace `FAMILY_UUID` with that UUID. `token` requires an already provisioned
family, `JWT_SECRET` of at least 32 characters and a lifetime from 1 to 24 hours.
Its output is a bearer credential: deliver it privately and keep it out of logs,
screenshots, Git and public reports. There is no public token-minting endpoint.
The reserved alias-quarantine family cannot receive a token from this CLI.
For Compose, the equivalent operator invocation is
`docker compose run --rm api python -m app.admin init-db`, with the appropriate
subcommand for provisioning or token issuance.

## New disposable/local database

For a local SQLite database, use a persistent file URL such as
`sqlite:////absolute/private/path/family-ledger.db`. The directory must already
exist and must remain accessible only to the application/operator. A container
SQLite file must be on a mounted volume to survive container replacement.
SQLite foreign keys are enabled on every connection. In-memory URLs use a
single shared connection pool so a session/thread handoff does not silently
create a different database; those databases disappear when their engine ends.

For PostgreSQL Compose, set `JWT_SECRET` and `POSTGRES_PASSWORD` in the deployment
environment or an untracked `.env` file before `docker compose up --build`.
Use a strong random JWT secret and a distinct database password; neither is
provided by the repository. `POSTGRES_PASSWORD` is interpolated into a URL, so
use a URL-safe value (for example a generated hexadecimal secret) or provide a
correctly percent-encoded connection URL when configuring the app separately.
Keep secrets out of Git, logs and public diagnostic records.

The API receives the synchronous PostgreSQL URL and required JWT secret.
PostgreSQL must pass `pg_isready` before Compose starts the API. Its data resides
in the named `pgdata` volume. The database port is not published on the host;
access it through the private Compose network or an explicitly authorized
operator session. A readiness check is not a migration or data-backup check.
The API port is published on 8000; external TLS and network exposure policy
belong to the deployment configuration.

## Upgrade an existing schema

This release changes the persistence model, including new state used by
confirmation/idempotency/inventory and the removal of unsafe alias uniqueness.
Existing PostgreSQL or SQLite databases **must not be assumed compatible**.
`Base.metadata.create_all()` can create missing tables but does not add columns
to existing tables or remove old uniqueness constraints. An explicit, bounded
upgrade is provided by `python -m app.admin migrate-db`; the engine/session
helpers and app imports never invoke it automatically.

1. Identify the running application version and actual schema. Stop writes and
   create an engine-appropriate backup (`pg_dump` for PostgreSQL, or a consistent
   SQLite backup while writes are stopped). Test that the backup can be restored.
2. Review the 0.2.0 ORM diff and the supported migration against the installed
   schema. Unknown alias columns/constraints, custom SQLite triggers/indexes or
   inbound alias references require a separate reviewed migration; this bounded
   upgrader refuses those layouts instead of discarding their data or behavior.
3. Restore a copy into a disposable staging database and explicitly run
   `python -m app.admin migrate-db`, then
   test multi-family isolation, existing receipt reads, idempotency, confirmation,
   rollback and inventory projection with the 0.2.0 application.
4. Only after the migration and its validation are reviewed, apply it during a
   controlled maintenance window. Record application/schema versions and check
   results before resuming writes.

The supported legacy upgrade preserves alias row IDs and values, adds nullable
`family_id`, assigns aliases of private products to that product's owner and
replaces `uq_alias_per_market` with `uq_alias_scoped`. The old schema does not
identify who learned an alias pointing to a global product. Those legacy aliases
are **not made globally visible**: they are assigned to the reserved quarantine
family `23acf3ed-7198-5212-a485-816bec4f4dcb`, named
`__alias_quarantine_only_v020__`. The UUID is a fixed UUIDv5 of the URL
`https://github.com/GuiMiran/family-ledger/alias-quarantine/v0.2`; it is not a
normal household or login identity. The row is created transactionally only
when a legacy global-product alias needs quarantine. If that reserved UUID is
already occupied by an unrelated family, the upgrade refuses to proceed.

Both product and alias ownership filters apply, so normal families and shared-
catalog callers cannot resolve quarantined aliases even though the underlying
product is global. `token` refuses the reserved UUID. The command prints
`quarantined_aliases_requiring_owner_review` and a warning. An authorized owner
must review each retained alias's provenance, record the decision, and explicitly
assign its real family or set `family_id=NULL` only when sharing is approved.
Review is an offline operator task, not a public reassignment endpoint; do not
infer an owner or release the whole quarantine automatically. Alias row IDs and
values remain available for that review. Current aliases are not reassigned on a
repeat migration, so a recorded explicit review decision is preserved.

PostgreSQL applies alias ALTER/backfill and new-table creation in one transaction
with a table lock. SQLite explicitly begins a write transaction, rebuilds only
the alias table, checks copied IDs/counts and foreign-key integrity, then creates
the new tables. An error rolls back the operation; the failed migration is not
reported as current. This is transactional schema handling, not a substitute for
the tested pre-upgrade backup or a zero-downtime migration claim.

If the upgrade fails, restore the pre-upgrade backup with the matching prior
application version. Reverting Python code alone cannot undo a schema or data
change. Do not delete `pgdata` or run `docker compose down -v` against data you
intend to preserve. For a genuinely empty disposable environment, explicit
schema initialization may create a new database; that is not a data migration.

## Verification scope

`tests/test_db_session.py` checks PostgreSQL URL normalization without contacting
a server, SQLite foreign-key enforcement, memory-session/thread behavior and
persistent-file data after engine recreation. These tests do not substitute for
PostgreSQL integration tests, schema-migration rehearsal or a deployed service
check. Installation success proves package assembly and declared imports, not
operational readiness.

`tests/test_migrations.py` exercises the explicit upgrade on a synthetic legacy
SQLite database with shared/private aliases, preserved IDs/values, reruns,
unknown-schema rejection and an injected failure after the alias rebuild that
must restore the old schema and rows. Offline provisioning/token tests use
synthetic families only. The tests also challenge quarantined-alias invisibility,
lazy reserved-family creation, collision handling, token refusal, rollback of
the reserved row and explicit owner-approved alias release. PostgreSQL migration behavior still requires the
separate real-engine integration run; no user database is migrated by tests.
