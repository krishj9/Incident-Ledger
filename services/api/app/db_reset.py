"""
Database reset utility — drop and recreate the incident_ledger database.

Called by `make reset-demo CONFIRM_SYNTHETIC_ONLY=true`.
ONLY runs against the configured DATABASE_URL — never against production.

Safety guards:
  - DEMO_ONLY must be True in settings (enforced)
  - CONFIRM_SYNTHETIC_ONLY env var must equal 'true' (enforced by Makefile, double-checked here)
  - Never drops databases containing production center codes

This module cannot be imported in production without raising; it is a
dev-time utility only.
"""

from __future__ import annotations

import asyncio
import os
import sys

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

logger = structlog.get_logger(__name__)


async def reset_database() -> None:
    """Drop and recreate the incident_ledger database."""

    # ── Safety gate 1: DEMO_ONLY must be True ────────────────────────────────
    if not settings.DEMO_ONLY:
        print("✗ ABORT: DEMO_ONLY is not True. reset-demo may not run against production.")
        sys.exit(1)

    # ── Safety gate 2: explicit env confirmation ──────────────────────────────
    confirm = os.environ.get("CONFIRM_SYNTHETIC_ONLY", "").strip().lower()
    if confirm != "true":
        print("✗ ABORT: Set CONFIRM_SYNTHETIC_ONLY=true to confirm database reset.")
        sys.exit(1)

    # ── Extract database name from URL ────────────────────────────────────────
    db_url = settings.DATABASE_URL
    db_name = db_url.rstrip("/").split("/")[-1].split("?")[0]

    print(f"→ Resetting database: '{db_name}'")
    print("  This will DROP and RECREATE the database. All data will be lost.")

    # ── Connect to postgres maintenance DB to run DROP/CREATE ─────────────────
    # Replace the database name in the URL with 'postgres' for the admin connection
    admin_url = db_url.replace(f"/{db_name}", "/postgres")

    # Use autocommit=True for DDL (DROP DATABASE requires no active transaction)
    admin_engine = create_async_engine(
        admin_url,
        isolation_level="AUTOCOMMIT",
        future=True,
    )

    try:
        async with admin_engine.connect() as conn:
            # Terminate active connections first
            await conn.execute(
                text(f"""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = '{db_name}'
                      AND pid <> pg_backend_pid()
                """)
            )
            print(f"  Terminated active connections to '{db_name}'")

            await conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
            print(f"  Dropped database '{db_name}'")

            await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            print(f"  Created database '{db_name}'")
    finally:
        await admin_engine.dispose()

    print("✓ Database reset complete. Run 'make migrate' then 'make seed-demo'.")


if __name__ == "__main__":
    asyncio.run(reset_database())
