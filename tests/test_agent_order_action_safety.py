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


@pytest.mark.asyncio
async def test_customer_cancellation_updates_status_and_history_in_one_transaction(
    monkeypatch,
):
    order = SimpleNamespace(id=17, order_number="RST1-000017", status="pending")
    class Session:
        async def __aenter__(self):
            return self

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


@pytest.mark.asyncio
async def test_modify_order_requires_confirmation_and_calls_business_service(monkeypatch):
    order = SimpleNamespace(id=17, order_number="RST1-000017", total_amount=300.0)
    item = SimpleNamespace(product_name="Pizza", quantity=3)

    class Session:
        async def __aenter__(self):
            return self

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


@pytest.mark.asyncio
async def test_executor_does_not_return_raw_exception_details():
    class FailingAction(BaseAction):
        def __init__(self):
            super().__init__(name="view_menu")

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
