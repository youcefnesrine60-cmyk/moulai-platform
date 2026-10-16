# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify real owner statistics and canonical repository method contracts."""

from datetime import (
    UTC,
    datetime,
)
from typing import Any
from unittest.mock import (
    AsyncMock,
    MagicMock,
    create_autospec,
)

import pytest
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.repositories.owner_repo import OwnerRepository
from app.schemas.owner import (
    OwnerResponse,
    OwnerStatusUpdate,
    OwnerUpdate,
)
from app.services.business.owner_service import OwnerService

# ==============================================
# OWNER DATA
# ==============================================


def owner_record() -> OwnerResponse:
    """Build a valid owner DTO without a database or network connection."""
    return OwnerResponse(
        id=17,
        chat_id=425,
        full_name="Owner Example",
        phone=None,
        email=None,
        registration_status="approved",
        trial_used=False,
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )


# ==============================================
# ACTUAL AGGREGATION QUERY
# ==============================================


@pytest.mark.asyncio
async def test_owner_statistics_count_real_trial_flags_and_legacy_nulls() -> None:
    """Execute the repository aggregate against rows with distinct trial states."""
    metadata = MetaData()
    owners = Table(
        "owners",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("registration_status", String(50), nullable=False),
        Column("trial_used", Boolean, nullable=True),
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            owners.insert(),
            [
                {"id": 1, "registration_status": "approved", "trial_used": True},
                {"id": 2, "registration_status": "approved", "trial_used": False},
                {"id": 3, "registration_status": "pending", "trial_used": False},
                {"id": 4, "registration_status": "rejected", "trial_used": None},
            ],
        )

    async def execute(statement: Select[Any]) -> MagicMock:
        """Run the exact SQLAlchemy statement and expose its fetched mapping."""
        with engine.connect() as connection:
            row = dict(connection.execute(statement).mappings().one())
        result = MagicMock()
        result.mappings.return_value.one.return_value = row
        return result

    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock(side_effect=execute)
    try:
        statistics = await OwnerRepository(session=session).get_statistics()
    finally:
        engine.dispose()

    assert statistics == {
        "total": 4,
        "pending": 1,
        "approved": 2,
        "rejected": 1,
        "trial_used": 1,
        "trial_available": 3,
    }
    session.execute.assert_awaited_once()


# ==============================================
# CANONICAL BASE REPOSITORY METHODS
# ==============================================


@pytest.mark.asyncio
async def test_owner_service_lookup_uses_the_canonical_primary_key_argument() -> None:
    """The removed owner_id compatibility wrapper is never needed for lookups."""
    service = OwnerService(session=MagicMock(spec=AsyncSession))
    service.repo = create_autospec(OwnerRepository, instance=True)
    service.repo.get_by_id.return_value = owner_record()

    result = await service.get_owner_by_id(owner_id=17)

    assert result.id == 17
    service.repo.get_by_id.assert_awaited_once_with(id=17)


@pytest.mark.asyncio
async def test_owner_profile_update_uses_the_canonical_primary_key_argument() -> None:
    """Profile mutations follow BaseRepository.update instead of removed wrappers."""
    service = OwnerService(session=MagicMock(spec=AsyncSession))
    service.repo = create_autospec(OwnerRepository, instance=True)
    service.repo.get_by_id.return_value = owner_record()
    service.repo.update.return_value = owner_record()

    result = await service.update_owner(
        owner_id=17,
        update_data=OwnerUpdate(full_name="Updated Owner", phone=None),
    )

    assert result.id == 17
    service.repo.update.assert_awaited_once_with(
        id=17,
        data={"full_name": "Updated Owner", "phone": None},
    )


@pytest.mark.asyncio
async def test_owner_status_update_uses_the_canonical_primary_key_argument() -> None:
    """Administrative status changes keep the canonical repository interface."""
    service = OwnerService(session=MagicMock(spec=AsyncSession))
    service.repo = create_autospec(OwnerRepository, instance=True)
    service.repo.update.return_value = owner_record()

    result = await service.update_owner_status(
        owner_id=17,
        status_data=OwnerStatusUpdate(registration_status="approved"),
    )

    assert result.id == 17
    service.repo.update.assert_awaited_once_with(
        id=17,
        data={"registration_status": "approved"},
    )


@pytest.mark.asyncio
async def test_owner_delete_uses_the_canonical_primary_key_argument() -> None:
    """Deletion checks associated restaurants and delegates with the primary key."""
    service = OwnerService(session=MagicMock(spec=AsyncSession))
    service.repo = create_autospec(OwnerRepository, instance=True)
    service.repo.get_by_id.return_value = owner_record()
    service.repo.count_restaurants.return_value = 0
    service.repo.delete.return_value = True

    await service.delete_owner(owner_id=17)

    service.repo.count_restaurants.assert_awaited_once_with(owner_id=17)
    service.repo.delete.assert_awaited_once_with(id=17)


@pytest.mark.asyncio
async def test_owner_statistics_service_uses_a_single_repository_snapshot() -> None:
    """Counters from separate transactions cannot be mixed into one response."""
    service = OwnerService(session=MagicMock(spec=AsyncSession))
    service.repo = create_autospec(OwnerRepository, instance=True)
    service.repo.get_statistics.return_value = {"total": 4, "trial_used": 1}

    result = await service.get_owner_statistics()

    assert result == {"total": 4, "trial_used": 1}
    service.repo.get_statistics.assert_awaited_once_with()
