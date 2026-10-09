# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# TEST MODULE - TESTS / TEST REPOSITORY TRANSACTION MODE
# Automated test coverage for the MoulAI platform.
# ==============================================

"""Automated tests for test repository transaction mode.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from types import SimpleNamespace

import pytest

from app.repositories.base import BaseRepository


class FakeSession:
    # ==============================================
    #   INIT
    # ==============================================

    def __init__(self, *, defer_commit: bool):
        self.info = {"defer_repository_commit": defer_commit}
        self.flushes = 0
        self.commits = 0
        self.rollbacks = 0

    # ==============================================
    # FLUSH
    # ==============================================

    async def flush(self):
        self.flushes += 1

    # ==============================================
    # COMMIT
    # ==============================================

    async def commit(self):
        self.commits += 1

    # ==============================================
    # ROLLBACK
    # ==============================================

    async def rollback(self):
        self.rollbacks += 1


# ==============================================
# TEST REPOSITORY UPDATE DEFERS COMMIT INSIDE COMPOSED TRANSACTION
# ==============================================


@pytest.mark.asyncio
async def test_repository_update_defers_commit_inside_composed_transaction():
    session = FakeSession(defer_commit=True)
    entity = SimpleNamespace(status="pending")
    repository = BaseRepository.__new__(BaseRepository)
    repository.model = type("FakeOrder", (), {})
    repository.session = session

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(*, id):
        return entity

    repository.get_by_id = get_by_id

    updated = await repository.update(id=1, data={"status": "cancelled"})

    assert updated is entity
    assert entity.status == "cancelled"
    assert session.flushes == 1
    assert session.commits == 0
    assert session.rollbacks == 0


# ==============================================
# TEST REPOSITORY UPDATE KEEPS DEFAULT COMMIT BEHAVIOR
# ==============================================


@pytest.mark.asyncio
async def test_repository_update_keeps_default_commit_behavior():
    session = FakeSession(defer_commit=False)
    entity = SimpleNamespace(status="pending")
    repository = BaseRepository.__new__(BaseRepository)
    repository.model = type("FakeOrder", (), {})
    repository.session = session

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(*, id):
        return entity

    repository.get_by_id = get_by_id

    await repository.update(id=1, data={"status": "cancelled"})

    assert session.commits == 1


# ==============================================
# TEST ORDER REPOSITORIES NEVER COMMIT OR ROLLBACK THE CALLERS TRANSACTION
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "repository_name",
    [
        "OrdersRepository",
        "OrderItemsRepository",
        "OrderItemOptionsRepository",
        "OrderStatusHistoryRepository",
        "OrderPaymentsRepository",
    ],
)
async def test_order_repositories_never_commit_or_rollback_the_callers_transaction(
    repository_name,
):
    from app.repositories.orders_repo import OrdersRepository
    from app.repositories.order_items_repo import OrderItemsRepository
    from app.repositories.order_item_options_repo import OrderItemOptionsRepository
    from app.repositories.order_status_history_repo import OrderStatusHistoryRepository
    from app.repositories.order_payments_repo import OrderPaymentsRepository

    repository_types = {
        "OrdersRepository": OrdersRepository,
        "OrderItemsRepository": OrderItemsRepository,
        "OrderItemOptionsRepository": OrderItemOptionsRepository,
        "OrderStatusHistoryRepository": OrderStatusHistoryRepository,
        "OrderPaymentsRepository": OrderPaymentsRepository,
    }
    repository_type = repository_types[repository_name]
    session = FakeSession(defer_commit=False)
    repository = repository_type(session=session)
    entity = SimpleNamespace(status="pending")

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(*, id):
        return entity

    repository.get_by_id = get_by_id
    await repository.update(id=1, data={"status": "confirmed"})
    assert session.flushes == 1
    assert session.commits == 0
    assert session.rollbacks == 0
