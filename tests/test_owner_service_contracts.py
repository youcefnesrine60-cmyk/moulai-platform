# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OWNER SERVICE CONTRACTS
# SQLAlchemy owner-service query contracts.
# ==============================================

"""Unit contracts for OwnerService methods replacing compatibility functions."""

from datetime import (
    UTC,
    datetime,
)
from unittest.mock import (
    AsyncMock,
    MagicMock,
)

import pytest

from app.services.business.owner_service import OwnerService

# ==============================================
# OWNER CREATION TIMESTAMP
# ==============================================


@pytest.mark.asyncio
async def test_get_created_at_delegates_to_the_owner_repository() -> None:
    """The service exposes creation time without a module-level repository wrapper."""
    created_at = datetime(2026, 1, 2, tzinfo=UTC)
    service = OwnerService(session=MagicMock())
    service.repo = MagicMock()
    service.repo.get_created_at = AsyncMock(return_value=created_at)

    result = await service.get_created_at(owner_id=17)

    assert result == created_at
    service.repo.get_created_at.assert_awaited_once_with(owner_id=17)
