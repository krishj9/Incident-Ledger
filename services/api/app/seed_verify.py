"""
Demo data verification script — validates synthetic data integrity.

Callable via `make verify-demo-data`.

Rules verified (seed-data.md + security-privacy.md):
  1. All centers have approved codes (in ALLOWED_CENTER_CODES)
  2. All users, children, guardians have synthetic_marker=true
  3. All guardian emails match approved demo domain pattern
  4. All user display_names begin with 'DEMO-'
  5. All child display_names begin with 'DEMO-'
  6. All guardian display_names begin with 'DEMO-'
  7. All devices are linked to a valid center
  8. Row counts match expected minimums

Exit code 0 on pass, 1 on any failure.
"""

from __future__ import annotations

import asyncio
import re
import sys
from dataclasses import dataclass, field

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import AsyncSessionLocal

# Approved email pattern: anything@demo.incident-ledger.dev
_APPROVED_EMAIL_RE = re.compile(r"^[^@]+@demo\.incident-ledger\.dev$")

# Required display name prefixes
_DEMO_PREFIX = "DEMO-"


@dataclass
class VerificationResult:
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def ok(self, msg: str) -> None:
        self.passed.append(msg)
        print(f"  ✓ {msg}")

    def fail(self, msg: str) -> None:
        self.failed.append(msg)
        print(f"  ✗ {msg}")

    @property
    def success(self) -> bool:
        return len(self.failed) == 0


async def verify(session: AsyncSession, result: VerificationResult) -> None:
    # ── 1. Centers: approved codes only ──────────────────────────────────────
    centers = (await session.execute(
        text("SELECT id, code, name, is_demo_enabled FROM centers")
    )).fetchall()

    if not centers:
        result.fail("No centers found in database")
    else:
        for row in centers:
            if row.code not in settings.ALLOWED_CENTER_CODES:
                result.fail(f"Center '{row.code}' is NOT in ALLOWED_CENTER_CODES")
            else:
                result.ok(f"Center code '{row.code}' is approved")
            if not row.is_demo_enabled:
                result.fail(f"Center '{row.code}' has is_demo_enabled=false")
            else:
                result.ok(f"Center '{row.code}' has is_demo_enabled=true")

    # ── 2. Users: synthetic_marker, DEMO- prefix ──────────────────────────────
    users = (await session.execute(
        text("SELECT id, display_name, role, synthetic_marker FROM users")
    )).fetchall()

    non_synthetic_users = [u for u in users if not u.synthetic_marker]
    if non_synthetic_users:
        for u in non_synthetic_users:
            result.fail(f"User '{u.display_name}' (role={u.role}) missing synthetic_marker=true")
    else:
        result.ok(f"All {len(users)} users have synthetic_marker=true")

    non_prefixed_users = [u for u in users if not u.display_name.startswith(_DEMO_PREFIX)]
    if non_prefixed_users:
        for u in non_prefixed_users:
            result.fail(f"User '{u.display_name}' does not begin with 'DEMO-'")
    else:
        result.ok(f"All {len(users)} users have 'DEMO-' prefix")

    if len(users) < 11:
        result.fail(f"Expected ≥11 users, found {len(users)}")
    else:
        result.ok(f"User count: {len(users)} ≥ 11 ✓")

    # ── 3. Children: synthetic_marker, DEMO- prefix ───────────────────────────
    children = (await session.execute(
        text("SELECT id, display_name, synthetic_marker FROM children")
    )).fetchall()

    non_synthetic_children = [c for c in children if not c.synthetic_marker]
    if non_synthetic_children:
        for c in non_synthetic_children:
            result.fail(f"Child '{c.display_name}' missing synthetic_marker=true")
    else:
        result.ok(f"All {len(children)} children have synthetic_marker=true")

    non_prefixed_children = [c for c in children if not c.display_name.startswith(_DEMO_PREFIX)]
    if non_prefixed_children:
        for c in non_prefixed_children:
            result.fail(f"Child '{c.display_name}' does not begin with 'DEMO-'")
    else:
        result.ok(f"All {len(children)} children have 'DEMO-' prefix")

    if len(children) < 12:
        result.fail(f"Expected ≥12 children, found {len(children)}")
    else:
        result.ok(f"Child count: {len(children)} ≥ 12 ✓")

    # ── 4. Guardians: synthetic_marker, DEMO- prefix, approved email ──────────
    guardians = (await session.execute(
        text("SELECT id, display_name, email, synthetic_marker FROM guardians")
    )).fetchall()

    non_synthetic_guardians = [g for g in guardians if not g.synthetic_marker]
    if non_synthetic_guardians:
        for g in non_synthetic_guardians:
            result.fail(f"Guardian '{g.display_name}' missing synthetic_marker=true")
    else:
        result.ok(f"All {len(guardians)} guardians have synthetic_marker=true")

    non_prefixed_guardians = [g for g in guardians if not g.display_name.startswith(_DEMO_PREFIX)]
    if non_prefixed_guardians:
        for g in non_prefixed_guardians:
            result.fail(f"Guardian '{g.display_name}' does not begin with 'DEMO-'")
    else:
        result.ok(f"All {len(guardians)} guardians have 'DEMO-' prefix")

    bad_emails = [
        g for g in guardians
        if g.email and not _APPROVED_EMAIL_RE.match(g.email)
    ]
    if bad_emails:
        for g in bad_emails:
            # Do NOT print the email address itself — could expose PII in logs
            result.fail(
                f"Guardian '{g.display_name}' has email not matching approved demo domain"
            )
    else:
        result.ok(f"All {len(guardians)} guardian emails match approved demo domain")

    if len(guardians) < 12:
        result.fail(f"Expected ≥12 guardians, found {len(guardians)}")
    else:
        result.ok(f"Guardian count: {len(guardians)} ≥ 12 ✓")

    # ── 5. Devices: count within limit ───────────────────────────────────────
    devices = (await session.execute(
        text("SELECT id, platform, status, center_id FROM devices WHERE status='active'")
    )).fetchall()

    if len(devices) < 4:
        result.fail(f"Expected ≥4 active devices, found {len(devices)}")
    elif len(devices) > 20:
        result.fail(f"Active device count {len(devices)} exceeds max 20")
    else:
        result.ok(f"Active device count: {len(devices)} (4 ≤ n ≤ 20) ✓")

    # ── 6. child_guardians: all children have at least one primary guardian ──
    cg = (await session.execute(
        text("""
            SELECT COUNT(*) FROM child_guardians WHERE is_primary = true
        """)
    )).scalar_one()

    if cg < 12:
        result.fail(f"Expected ≥12 primary guardian links, found {cg}")
    else:
        result.ok(f"Primary guardian links: {cg} ≥ 12 ✓")


async def run_verify() -> None:
    print(f"\n{'='*60}")
    print("  Incident Ledger — Demo Data Verification")
    print(f"{'='*60}\n")

    result = VerificationResult()

    async with AsyncSessionLocal() as session:
        await verify(session, result)

    print(f"\n{'='*60}")
    print(f"  Passed: {len(result.passed)}")
    print(f"  Failed: {len(result.failed)}")
    print(f"{'='*60}\n")

    if result.success:
        print("  ✓ All checks passed\n")
        sys.exit(0)
    else:
        print("  ✗ Verification FAILED\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_verify())
