# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Reject inconsistent conversation parents before reuse or persistence."""

# ==============================================
# IMPORTS
# ==============================================

from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    create_autospec,
)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)
from app.repositories.agent.agent_repo import AgentRepository
from app.repositories.agent.channel_repo import ChannelRepository
from app.repositories.agent.conversation_repo import ConversationRepository
from app.schemas.agent.conversation import ConversationCreate
from app.services.business.agent.conversation_service import ConversationService

# ==============================================
# PARENT CONSISTENCY
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("has_existing_conversation", [False, True])
async def test_conversation_rejects_channel_from_another_agent_before_reuse(
    *,
    has_existing_conversation: bool,
) -> None:
    """A valid agent and channel are insufficient when their relationship differs."""
    session = AsyncSession()
    session.commit = AsyncMock()
    service = ConversationService(session=session, owner_id=1)
    service.agent_repo = create_autospec(AgentRepository, instance=True)
    service.channel_repo = create_autospec(ChannelRepository, instance=True)
    service.repo = create_autospec(ConversationRepository, instance=True)
    service.agent_repo.get_by_id.return_value = SimpleNamespace(id=7)
    service.channel_repo.get_by_id.return_value = SimpleNamespace(id=9, agent_id=8)
    service.repo.get_by_user_id.return_value = (
        SimpleNamespace(id=11) if has_existing_conversation else None
    )

    with pytest.raises(ValidationError, match="Channel does not belong"):
        await service.create(
            conversation_data=ConversationCreate(
                agent_id=7,
                channel_id=9,
                user_id="customer-41",
            ),
        )

    service.repo.get_by_user_id.assert_not_awaited()
    service.repo.create.assert_not_awaited()
    session.commit.assert_not_awaited()
    await session.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_parent", ["agent", "channel"])
async def test_conversation_missing_parent_cannot_reuse_an_existing_record(
    *,
    missing_parent: str,
) -> None:
    """Missing or tenant-filtered parents stop work before conversation lookup."""
    session = AsyncSession()
    session.commit = AsyncMock()
    service = ConversationService(session=session, owner_id=1)
    service.agent_repo = create_autospec(AgentRepository, instance=True)
    service.channel_repo = create_autospec(ChannelRepository, instance=True)
    service.repo = create_autospec(ConversationRepository, instance=True)
    service.agent_repo.get_by_id.return_value = (
        None if missing_parent == "agent" else SimpleNamespace(id=7)
    )
    service.channel_repo.get_by_id.return_value = (
        None if missing_parent == "channel" else SimpleNamespace(id=9, agent_id=7)
    )

    with pytest.raises(NotFoundError):
        await service.create(
            conversation_data=ConversationCreate(
                agent_id=7,
                channel_id=9,
                user_id="customer-41",
            ),
        )

    service.repo.get_by_user_id.assert_not_awaited()
    service.repo.create.assert_not_awaited()
    session.commit.assert_not_awaited()
    await session.close()
