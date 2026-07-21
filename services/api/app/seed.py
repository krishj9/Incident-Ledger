"""
Demo seed script — inserts the full synthetic base roster.

Rules (seed-data.md + security-privacy.md):
  - All records set synthetic_marker=true
  - All display names begin with 'DEMO-'
  - All emails use approved demo domain: demo.incident-ledger.dev
  - Deterministic UUIDv7s derived from SEED_VERSION so re-running is idempotent
  - ON CONFLICT DO NOTHING on every insert — safe to re-run
  - DO NOT create scenario fixtures (S01-S12) — base roster only

Usage:
    make seed-demo                   # SEED_VERSION=1 (default)
    make seed-demo SEED_VERSION=1    # explicit

Seeded entities:
  - 1 center (DEMO-MGLC-01)
  - 11 users (6 staff, 1 director, 1 backup, 1 regional, 1 compliance, 1 ops)
  - 12 children (Sunflower: 6, Bluebird: 6)
  - 12 guardians (one per child)
  - 12 child_guardians links
  - 5 devices (iOS/iPadOS, assigned to staff/director)
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import AsyncSessionLocal
from app.models.base import generate_uuid7
from app.seed_scenarios import seed_scenarios

logger = structlog.get_logger(__name__)

# ── Seed version ───────────────────────────────────────────────────────────────
SEED_VERSION = int(os.environ.get("SEED_VERSION", "1"))

# ── Demo domain (approved in security-privacy.md) ─────────────────────────────
DEMO_EMAIL_DOMAIN = "demo.incident-ledger.dev"

# ── Allowed center code ────────────────────────────────────────────────────────
CENTER_CODE = "DEMO-MGLC-01"


# ── Deterministic UUID generation ─────────────────────────────────────────────

def det_uuid(namespace: str, name: str) -> uuid.UUID:
    """
    Generate a deterministic UUID from a namespace + name string.

    Uses UUID5 (SHA-1-based) seeded with the SEED_VERSION so every run of
    the same seed version produces identical IDs.

    The UUID5 output is not a UUIDv7 but is stable across re-runs —
    the ON CONFLICT DO NOTHING guards handle idempotency.
    """
    ns = uuid.UUID(hashlib.sha1(  # noqa: S324 — not for crypto
        f"incident-ledger-seed-v{SEED_VERSION}".encode()
    ).hexdigest()[:32])
    return uuid.uuid5(ns, name)


# ── Roster definitions ────────────────────────────────────────────────────────

CENTER_ID = det_uuid("center", CENTER_CODE)

USERS: list[dict[str, Any]] = [
    # Staff (6)
    {"slug": "alex-kim",    "display_name": "DEMO-Alex Kim",     "role": "staff"},
    {"slug": "sam-torres",  "display_name": "DEMO-Sam Torres",   "role": "staff"},
    {"slug": "jamie-lee",   "display_name": "DEMO-Jamie Lee",    "role": "staff"},
    {"slug": "morgan-davis","display_name": "DEMO-Morgan Davis", "role": "staff"},
    {"slug": "taylor-nguyen","display_name": "DEMO-Taylor Nguyen","role": "staff"},
    {"slug": "drew-patel",  "display_name": "DEMO-Drew Patel",   "role": "staff"},
    # Director
    {"slug": "maya-chen",   "display_name": "DEMO-Maya Chen",    "role": "director"},
    # Backup director
    {"slug": "jordan-patel","display_name": "DEMO-Jordan Patel", "role": "backup_director"},
    # Regional admin
    {"slug": "avery-brooks","display_name": "DEMO-Avery Brooks", "role": "regional_admin"},
    # Compliance reviewer
    {"slug": "riley-morgan","display_name": "DEMO-Riley Morgan", "role": "compliance_reviewer"},
    # Operations support
    {"slug": "casey-rivera","display_name": "DEMO-Casey Rivera", "role": "operations_support"},
]

# 12 children across two classrooms
CHILDREN: list[dict[str, Any]] = [
    # Sunflower classroom (6)
    {"slug": "child-01", "display_name": "DEMO-Child Sunflower 01", "classroom": "Sunflower"},
    {"slug": "child-02", "display_name": "DEMO-Child Sunflower 02", "classroom": "Sunflower"},
    {"slug": "child-03", "display_name": "DEMO-Child Sunflower 03", "classroom": "Sunflower"},
    {"slug": "child-04", "display_name": "DEMO-Child Sunflower 04", "classroom": "Sunflower"},
    {"slug": "child-05", "display_name": "DEMO-Child Sunflower 05", "classroom": "Sunflower"},
    {"slug": "child-06", "display_name": "DEMO-Child Sunflower 06", "classroom": "Sunflower"},
    # Bluebird classroom (6)
    {"slug": "child-07", "display_name": "DEMO-Child Bluebird 07", "classroom": "Bluebird"},
    {"slug": "child-08", "display_name": "DEMO-Child Bluebird 08", "classroom": "Bluebird"},
    {"slug": "child-09", "display_name": "DEMO-Child Bluebird 09", "classroom": "Bluebird"},
    {"slug": "child-10", "display_name": "DEMO-Child Bluebird 10", "classroom": "Bluebird"},
    {"slug": "child-11", "display_name": "DEMO-Child Bluebird 11", "classroom": "Bluebird"},
    {"slug": "child-12", "display_name": "DEMO-Child Bluebird 12", "classroom": "Bluebird"},
]

# 5 device registrations (under 20 total; no user exceeds 3 per seed-data.md)
DEVICES: list[dict[str, Any]] = [
    {"slug": "dev-alex-iphone",   "user_slug": "alex-kim",    "platform": "ios",     "label": "DEMO-Alex iPhone"},
    {"slug": "dev-alex-ipad",     "user_slug": "alex-kim",    "platform": "ipados",  "label": "DEMO-Alex iPad"},
    {"slug": "dev-sam-iphone",    "user_slug": "sam-torres",  "platform": "ios",     "label": "DEMO-Sam iPhone"},
    {"slug": "dev-maya-ipad",     "user_slug": "maya-chen",   "platform": "ipados",  "label": "DEMO-Maya iPad"},
    {"slug": "dev-jamie-iphone",  "user_slug": "jamie-lee",   "platform": "ios",     "label": "DEMO-Jamie iPhone"},
]


# ── Insert helpers ─────────────────────────────────────────────────────────────

async def _exec(session: AsyncSession, sql: str, params: dict[str, Any]) -> None:
    """Execute a parameterized SQL statement with ON CONFLICT DO NOTHING semantics."""
    await session.execute(text(sql), params)


# ── Seed functions ─────────────────────────────────────────────────────────────

async def seed_center(session: AsyncSession) -> None:
    print(f"  Seeding center: {CENTER_CODE}")
    await _exec(
        session,
        """
        INSERT INTO centers (id, code, name, timezone, is_demo_enabled,
                             max_active_mobile_installations, synthetic_marker)
        VALUES (:id, :code, :name, :timezone, :is_demo_enabled,
                :max_installs, :synthetic_marker)
        ON CONFLICT (id) DO NOTHING
        """,
        {
            "id": CENTER_ID,
            "code": CENTER_CODE,
            "name": "DEMO-Maple Grove Learning Center",
            "timezone": "America/New_York",
            "is_demo_enabled": True,
            "max_installs": 20,
            "synthetic_marker": True,
        },
    )


async def seed_users(session: AsyncSession) -> dict[str, uuid.UUID]:
    """Seed all users. Returns slug → UUID mapping for downstream use."""
    user_ids: dict[str, uuid.UUID] = {}
    for u in USERS:
        uid = det_uuid("user", u["slug"])
        user_ids[u["slug"]] = uid
        external_subject = f"entra-demo-{u['slug']}"
        print(f"  Seeding user: {u['display_name']} ({u['role']})")
        await _exec(
            session,
            """
            INSERT INTO users (id, center_id, external_subject, display_name, role,
                               active, synthetic_marker)
            VALUES (:id, :center_id, :external_subject, :display_name, :role,
                    :active, :synthetic_marker)
            ON CONFLICT (id) DO NOTHING
            """,
            {
                "id": uid,
                "center_id": CENTER_ID,
                "external_subject": external_subject,
                "display_name": u["display_name"],
                "role": u["role"],
                "active": True,
                "synthetic_marker": True,
            },
        )
    return user_ids


async def seed_children_and_guardians(session: AsyncSession) -> None:
    """Seed 12 children, 12 guardians, and 12 child_guardian links (all primary)."""
    for i, child in enumerate(CHILDREN, start=1):
        child_id = det_uuid("child", child["slug"])
        guardian_id = det_uuid("guardian", f"guardian-{child['slug']}")
        guardian_email = f"demo-guardian-{i:02d}@{DEMO_EMAIL_DOMAIN}"

        print(f"  Seeding child+guardian: {child['display_name']} / guardian-{i:02d}")

        # Insert child
        await _exec(
            session,
            """
            INSERT INTO children (id, center_id, display_name, classroom, active, synthetic_marker)
            VALUES (:id, :center_id, :display_name, :classroom, :active, :synthetic_marker)
            ON CONFLICT (id) DO NOTHING
            """,
            {
                "id": child_id,
                "center_id": CENTER_ID,
                "display_name": child["display_name"],
                "classroom": child["classroom"],
                "active": True,
                "synthetic_marker": True,
            },
        )

        # Insert guardian
        await _exec(
            session,
            """
            INSERT INTO guardians (id, center_id, display_name, email, synthetic_marker)
            VALUES (:id, :center_id, :display_name, :email, :synthetic_marker)
            ON CONFLICT (id) DO NOTHING
            """,
            {
                "id": guardian_id,
                "center_id": CENTER_ID,
                "display_name": f"DEMO-Guardian {i:02d}",
                "email": guardian_email,
                "synthetic_marker": True,
            },
        )

        # Link child ↔ guardian (primary)
        await _exec(
            session,
            """
            INSERT INTO child_guardians (child_id, guardian_id, is_primary)
            VALUES (:child_id, :guardian_id, :is_primary)
            ON CONFLICT (child_id, guardian_id) DO NOTHING
            """,
            {
                "child_id": child_id,
                "guardian_id": guardian_id,
                "is_primary": True,
            },
        )


async def seed_devices(
    session: AsyncSession, user_ids: dict[str, uuid.UUID]
) -> None:
    """Seed 5 device registrations for selected staff."""
    for d in DEVICES:
        device_id = det_uuid("device", d["slug"])
        user_id = user_ids[d["user_slug"]]
        installation_id = f"demo-install-{d['slug']}-v{SEED_VERSION}"
        print(f"  Seeding device: {d['label']} ({d['platform']})")
        await _exec(
            session,
            """
            INSERT INTO devices (id, center_id, registered_user_id, installation_id,
                                 platform, device_label, status)
            VALUES (:id, :center_id, :registered_user_id, :installation_id,
                    :platform, :device_label, :status)
            ON CONFLICT (id) DO NOTHING
            """,
            {
                "id": device_id,
                "center_id": CENTER_ID,
                "registered_user_id": user_id,
                "installation_id": installation_id,
                "platform": d["platform"],
                "device_label": d["label"],
                "status": "active",
            },
        )


# ── Main ───────────────────────────────────────────────────────────────────────

async def run_seed() -> None:
    if not settings.DEMO_ONLY:
        print("✗ ABORT: DEMO_ONLY is not True. Seed script may not run against production.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Incident Ledger — Demo Seed (SEED_VERSION={SEED_VERSION})")
    print(f"{'='*60}\n")

    async with AsyncSessionLocal() as session:
        try:
            await seed_center(session)
            user_ids = await seed_users(session)
            await seed_children_and_guardians(session)
            await seed_devices(session, user_ids)
            await seed_scenarios(session, user_ids, det_uuid, SEED_VERSION, CENTER_ID)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            print(f"\n✗ Seed failed: {type(exc).__name__}: {exc}")
            raise

    print(f"\n{'='*60}")
    print(f"  ✓ Seed complete (SEED_VERSION={SEED_VERSION})")
    print(f"  Center:    {CENTER_CODE}")
    print(f"  Users:     {len(USERS)}")
    print(f"  Children:  {len(CHILDREN)}")
    print(f"  Guardians: {len(CHILDREN)}  (one per child)")
    print(f"  Devices:   {len(DEVICES)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(run_seed())
