"""Explicit offline database administration; no public family/token endpoint."""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

from sqlalchemy.exc import SQLAlchemyError

from app.core.auth import issue_family_token
from app.infrastructure.db.migrations import (
    ALIAS_QUARANTINE_FAMILY_ID, initialize_database, migrate_database, SchemaUpgradeError,
)
from app.infrastructure.db.orm import Family
from app.infrastructure.db.session import create_db_engine, create_session_factory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.admin")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db", help="Initialize empty/current database; refuse legacy schemas")
    commands.add_parser("migrate-db", help="Explicitly migrate supported legacy aliases after backup/review")
    family = commands.add_parser("create-family", help="Provision a family offline")
    family.add_argument("--name", required=True)
    token = commands.add_parser("token", help="Issue an expiring token for an existing family")
    token.add_argument("--family", type=uuid.UUID, required=True)
    token.add_argument("--hours", type=int, choices=range(1, 25), default=8)
    args = parser.parse_args(argv)
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 1
    engine = None
    try:
        if args.command == "token" and len(os.environ.get("JWT_SECRET", "")) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        if args.command == "token" and args.family == ALIAS_QUARANTINE_FAMILY_ID:
            raise ValueError("The reserved alias quarantine family cannot receive access tokens")
        if args.command == "create-family" and not args.name.strip():
            raise ValueError("Family name must not be blank")
        engine = create_db_engine(url)
        if args.command in {"init-db", "migrate-db"}:
            result = initialize_database(engine) if args.command == "init-db" else migrate_database(engine)
            print(json.dumps(result))
            if result.get("quarantined_aliases_requiring_owner_review"):
                print("Legacy aliases with unknown provenance remain quarantined pending owner review", file=sys.stderr)
        else:
            factory = create_session_factory(engine)
            if args.command == "create-family":
                with factory.begin() as session:
                    provisioned = Family(name=args.name.strip())
                    session.add(provisioned)
                    session.flush()
                    family_id = provisioned.id
                print(str(family_id))
            else:
                with factory() as session:
                    if session.get(Family, args.family) is None:
                        raise ValueError("Family is not provisioned")
                print(issue_family_token(os.environ["JWT_SECRET"], args.family, args.hours))
        return 0
    except (SchemaUpgradeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except SQLAlchemyError as error:
        # Do not print connection secrets, SQL parameters or personal row data.
        print(f"Database operation failed ({type(error).__name__}); inspect configuration/schema safely", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
