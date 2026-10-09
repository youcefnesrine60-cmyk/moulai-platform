# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# TEST MODULE - TESTS / TEST AGENT ORDER ACTION SAFETY
# Automated test coverage for the MoulAI platform.
# ==============================================

"""Automated tests for test agent order action safety.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.agent.executor.actions as actions
import app.services.business.orders.customer as customer_orders
from app.agent.executor.action_executor import ActionExecutor
from app.agent.executor.actions import (
    ActionRegistry,
    BaseAction,
    CancelOrderAction,
    ModifyOrderAction,
    TrackOrderAction,
)

# ==============================================
# TEST ORDER ACTIONS REQUIRE AN EXPLICIT ORDER REFERENCE
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("action_type", [CancelOrderAction, TrackOrderAction])
async def test_order_actions_require_an_explicit_order_reference(
    action_type,
    monkeypatch,
):
    monkeypatch.setattr(
        actions,
        "AsyncSessionLocal",
        lambda: pytest.fail("database must not be queried without an order reference"),
    )

    result = await action_type().execute(
        params={"order_id": "  "},
        context={"user_id": 425},
    )

    assert result.success is False
    assert result.error == "missing_order_id"


# ==============================================
# TEST OWNED ORDER LOOKUP NEVER DEFAULTS TO LATEST ORDER
# ==============================================


@pytest.mark.asyncio
async def test_owned_order_lookup_never_defaults_to_latest_order():
    session = SimpleNamespace(execute=AsyncMock())

    result = await customer_orders.get_customer_order(
        chat_id=425,
        order_reference=None,
        session=session,
    )

    assert result is None
    session.execute.assert_not_awaited()


# ==============================================
# TEST OWNED ORDER LOOKUP SCOPES BY CUSTOMER CHAT ID
# ==============================================


@pytest.mark.asyncio
async def test_owned_order_lookup_scopes_by_customer_chat_id():
    expected_order = object()
    result = SimpleNamespace(scalar_one_or_none=lambda: expected_order)
    session = SimpleNamespace(execute=AsyncMock(return_value=result))

    order = await customer_orders.get_customer_order(
        chat_id=425,
        order_reference="RST1-000017",
        session=session,
    )

    statement = session.execute.await_args.args[0]
    sql = str(statement)
    params = statement.compile().params
    assert order is expected_order
    assert "users.chat_id" in sql
    assert 425 in params.values()
    assert "orders.order_number" in sql


# ==============================================
# TEST CUSTOMER CANCELLATION UPDATES STATUS AND HISTORY IN ONE TRANSACTION
# ==============================================


@pytest.mark.asyncio
async def test_customer_cancellation_updates_status_and_history_in_one_transaction(
    monkeypatch,
):
    order = SimpleNamespace(id=17, order_number="RST1-000017", status="pending")

    class Session:
        # ==============================================
        #   AENTER
        # ==============================================

        async def __aenter__(self):
            return self

        # ==============================================
        #   AEXIT
        # ==============================================

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    session = Session()
    monkeypatch.setattr(actions, "AsyncSessionLocal", lambda: session)
    monkeypatch.setattr(
        actions,
        "cancel_customer_order",
        AsyncMock(return_value=(order, "pending")),
    )

    result = await CancelOrderAction().execute(
        params={"order_id": "RST1-000017"},
        context={"user_id": 425},
    )

    assert result.success is True
    assert result.data["previous_status"] == "pending"
    actions.cancel_customer_order.assert_awaited_once()


# ==============================================
# TEST MODIFY ORDER REQUIRES CONFIRMATION AND CALLS BUSINESS SERVICE
# ==============================================


@pytest.mark.asyncio
async def test_modify_order_requires_confirmation_and_calls_business_service(
    monkeypatch,
):
    order = SimpleNamespace(id=17, order_number="RST1-000017", total_amount=300.0)
    item = SimpleNamespace(product_name="Pizza", quantity=3)

    class Session:
        # ==============================================
        #   AENTER
        # ==============================================

        async def __aenter__(self):
            return self

        # ==============================================
        #   AEXIT
        # ==============================================

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(actions, "AsyncSessionLocal", Session)
    service = AsyncMock(return_value=(order, item))
    monkeypatch.setattr(actions, "change_customer_order_item_quantity", service)
    action = ModifyOrderAction()

    result = await action.execute(
        params={
            "order_id": "RST1-000017",
            "product_name": "Pizza",
            "quantity": 3,
        },
        context={"user_id": 425},
    )

    assert action.requires_confirmation is True
    assert result.success is True
    assert result.data["quantity"] == 3
    service.assert_awaited_once()


# ==============================================
# TEST TRACK ORDER RETURNS ONLY CUSTOMER SCOPED ORDER
# ==============================================


@pytest.mark.asyncio
async def test_track_order_returns_only_customer_scoped_order(monkeypatch):
    order = SimpleNamespace(
        id=17,
        order_number="RST1-000017",
        status="preparing",
        total_amount=850.0,
    )

    class Session:
        # ==============================================
        #   AENTER
        # ==============================================

        async def __aenter__(self):
            return self

        # ==============================================
        #   AEXIT
        # ==============================================

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(actions, "AsyncSessionLocal", Session)
    lookup = AsyncMock(return_value=order)
    monkeypatch.setattr(actions, "get_customer_order", lookup)

    result = await TrackOrderAction().execute(
        params={"order_id": "RST1-000017"},
        context={"user_id": 425},
    )

    assert result.success is True
    assert result.data["status"] == "preparing"
    lookup.assert_awaited_once()
    assert lookup.await_args.kwargs["chat_id"] == 425
    assert lookup.await_args.kwargs["order_reference"] == "RST1-000017"


# ==============================================
# TEST EXECUTOR STAGES MUTATION UNTIL USER CONFIRMATION
# ==============================================


@pytest.mark.asyncio
async def test_executor_stages_mutation_until_user_confirmation():
    registry = ActionRegistry()
    action = ModifyOrderAction()
    registry.register(action)
    executor = ActionExecutor(registry=registry)

    result = await executor.execute(
        intent_result={
            "intent": "modify_order",
            "confidence": 1.0,
            "entities": {
                "order_id": "RST1-000017",
                "product_name": "Pizza",
                "quantity": 3,
            },
            "language": "en",
        },
        context={
            "user_id": 425,
            "request_context": {"restaurant_id": 1},
        },
    )

    assert result["success"] is True
    assert result["data"]["pending_confirmation"] is True
    assert result["confirmed"] is False
    assert result["data"]["params"]["order_id"] == "RST1-000017"


# ==============================================
# TEST EXECUTOR DOES NOT RETURN RAW EXCEPTION DETAILS
# ==============================================


@pytest.mark.asyncio
async def test_executor_does_not_return_raw_exception_details():
    class FailingAction(BaseAction):
        # ==============================================
        #   INIT
        # ==============================================

        def __init__(self):
            super().__init__(name="view_menu")

        # ==============================================
        # EXECUTE
        # ==============================================

        async def execute(self, *, params, context=None):
            raise RuntimeError("database password and private query")

    registry = ActionRegistry()
    registry.register(FailingAction())
    executor = ActionExecutor(registry=registry)

    result = await executor.execute(
        intent_result={
            "intent": "view_menu",
            "confidence": 1.0,
            "entities": {},
            "language": "en",
        },
    )

    assert result["success"] is False
    assert result["error"] == "action_failed"
    assert "database password" not in result["error"]
