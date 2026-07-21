"""
Device repository — database access for the devices table.

Business rules:
  - center has max_active_mobile_installations (default 20) active devices
  - platform must be 'ios' or 'ipados'
  - installation_id is globally unique across centers
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.devices import Device


async def get_device_by_installation_id(
    session: AsyncSession,
    installation_id: str,
) -> Device | None:
    """Look up device by unique installation_id."""
    result = await session.execute(
        select(Device).where(Device.installation_id == installation_id).limit(1)
    )
    return result.scalar_one_or_none()


async def get_device_by_id(
    session: AsyncSession,
    device_id: uuid.UUID,
) -> Device | None:
    result = await session.execute(
        select(Device).where(Device.id == device_id).limit(1)
    )
    return result.scalar_one_or_none()


async def count_active_devices_for_center(
    session: AsyncSession,
    center_id: uuid.UUID,
) -> int:
    """Count devices with status='active' for a given center."""
    result = await session.execute(
        select(func.count()).where(
            Device.center_id == center_id,
            Device.status == "active",
        )
    )
    return result.scalar_one()


async def register_device(
    session: AsyncSession,
    *,
    device_id: uuid.UUID,
    center_id: uuid.UUID,
    registered_user_id: uuid.UUID,
    installation_id: str,
    platform: str,
    device_label: str,
) -> Device:
    """
    Insert a new device record with status='active'.

    Caller must have already validated:
    - center active device count < max_active_mobile_installations
    - platform is 'ios' or 'ipados'
    - installation_id is not already registered
    """
    device = Device(
        id=device_id,
        center_id=center_id,
        registered_user_id=registered_user_id,
        installation_id=installation_id,
        platform=platform,
        device_label=device_label,
        status="active",
    )
    session.add(device)
    return device
