from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.models.order import Order
from app.repositories.orders_repo import OrdersRepository
from app.services.business.orders import customer as customer_orders
from app.services.business.orders import cancel, read, status_history, totals, update


class FakeTransaction:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        self.committed = exc_type is None
        self.rolled_back = exc_type is not None
        return False


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, *, result=None, active_transaction=False):
        self.result = result
        self.active_transaction = active_transaction
        self.transaction = FakeTransaction()
        self.info = {}
        self.statements = []
        self.commits = 0

    def begin(self):
        return self.transaction

    def begin_nested(self):
        return self.transaction

    def get_transaction(self):
        return SimpleNamespace(sync_transaction=SimpleNamespace(origin=None))

    async def flush(self):
        pass

    def in_transaction(self):
        return self.active_transaction

    async def execute(self, statement):
        self.statements.append(statement)
        return ScalarResult(self.result)

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_status_change_updates_order_and_history_in_same_transaction(monkeypatch):
    order = SimpleNamespace(id=17, order_number="RST1-000017", status="pending")
    session = FakeSession(result=order)
    updates = []
    histories = []

    class OrdersRepository:
        def __init__(self, *, session):
            self.session = session

        async def update(self, *, id, data):
            updates.append((id, data.copy()))
            order.status = data["status"]
            return order

    class HistoryRepository:
        def __init__(self, *, session):
            self.session = session

        async def create(self, *, data):
            histories.append(data.copy())
            return data

    monkeypatch.setattr(update, "OrdersRepository", OrdersRepository)
    monkeypatch.setattr(update, "OrderStatusHistoryRepository", HistoryRepository)

    changed = await update.change_order_status(
        order_id=17,
        new_status="confirmed",
        employee_id=5,
        note="Accepted",
        session=session,
    )

    assert changed is order
    assert order.status == "confirmed"
    assert updates == []  # Tracked order mutation; the unit of work flushes it.
    assert histories == [{
        "order_id": 17,
        "old_status": "pending",
        "new_status": "confirmed",
        "changed_by_employee_id": 5,
        "note": "Accepted",
    }]
    assert session.transaction.committed is True
    assert session.info == {}


@pytest.mark.asyncio
async def test_status_change_preserves_callers_outer_transaction(monkeypatch):
    order = SimpleNamespace(id=17, order_number="RST1-000017", status="pending")
    session = FakeSession(result=order, active_transaction=True)

    class OrdersRepository:
        def __init__(self, *, session):
            self.session = session

        async def update(self, *, id, data):
            order.status = data["status"]
            return order

    class HistoryRepository:
        def __init__(self, *, session):
            pass

        async def create(self, *, data):
            return data

    monkeypatch.setattr(update, "OrdersRepository", OrdersRepository)
    monkeypatch.setattr(update, "OrderStatusHistoryRepository", HistoryRepository)

    await update.change_order_status(
        order_id=17,
        new_status="confirmed",
        session=session,
    )

    assert session.commits == 0
    assert session.info == {}


@pytest.mark.asyncio
async def test_status_change_rejects_invalid_and_disallowed_transitions(monkeypatch):
    order = SimpleNamespace(id=17, order_number="RST1-000017", status="completed")
    session = FakeSession(result=order)

    with pytest.raises(ValidationError):
        await update.change_order_status(
            order_id=17,
            new_status="not-a-status",
            session=session,
        )

    with pytest.raises(ValidationError):
        await update.change_order_status(
            order_id=17,
            new_status="cancelled",
            session=session,
        )

    assert session.transaction.rolled_back is True


@pytest.mark.asyncio
async def test_update_order_uses_repository_primary_key_signature(monkeypatch):
    order = SimpleNamespace(id=17, order_number="RST1-000017", status="pending")
    calls = []

    class OrdersRepository:
        def __init__(self, *, session):
            pass

        async def get_by_id(self, *, id):
            calls.append(("get", id))
            return order

        async def update(self, *, id, data):
            calls.append(("update", id, data.copy()))
            return order

    monkeypatch.setattr(update, "OrdersRepository", OrdersRepository)
    monkeypatch.setattr(update, "check_order_editable", lambda _: None)

    result = await update.update_order(
        order_id=17,
        data={"customer_note": "No onions", "status": "cancelled"},
        session=FakeSession(result=order),
    )

    assert result is order
    assert calls == [("update", 17, {"customer_note": "No onions"})]


@pytest.mark.asyncio
async def test_calculate_order_totals_includes_options_and_rounds(monkeypatch):
    order = SimpleNamespace(
        id=17,
        discount_amount=5.25,
        tax_amount=2.5,
        delivery_amount=10.0,
    )
    updated = []

    class OrdersRepository:
        def __init__(self, *, session):
            pass

        async def get_by_id(self, *, id):
            return order

        async def update(self, *, id, data):
            updated.append((id, data))

    class ItemsRepository:
        def __init__(self, *, session):
            pass

        async def get_by_order_id(self, *, order_id):
            return [
                SimpleNamespace(id=31, total_price=19.995),
                SimpleNamespace(id=32, total_price=10.0),
            ]

    class OptionsRepository:
        def __init__(self, *, session):
            pass

        async def get_by_order_item_id(self, *, order_item_id):
            return [SimpleNamespace(additional_price=1.505)] if order_item_id == 31 else []

    monkeypatch.setattr(totals, "OrdersRepository", OrdersRepository)
    monkeypatch.setattr(totals, "OrderItemsRepository", ItemsRepository)
    monkeypatch.setattr(totals, "OrderItemOptionsRepository", OptionsRepository)

    result = await totals.calculate_order_totals(
        order_id=17,
        session=FakeSession(),
        include_options=True,
    )

    assert result == (31.5, 5.25, 2.5, 10.0, 38.75)
    assert updated == [(
        17,
        {
            "subtotal_amount": 31.5,
            "discount_amount": 5.25,
            "tax_amount": 2.5,
            "delivery_amount": 10.0,
            "total_amount": 38.75,
        },
    )]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("subtotal_amount", -1),
        ("discount_amount", -1),
        ("tax_amount", -1),
        ("delivery_amount", -1),
        ("total_amount", -1),
    ],
)
async def test_update_totals_rejects_each_negative_component(field, value, monkeypatch):
    class UnexpectedRepository:
        def __init__(self, *, session):
            pytest.fail("Invalid totals must be rejected before database access")

    monkeypatch.setattr(totals, "OrdersRepository", UnexpectedRepository)
    values = {
        "subtotal_amount": 100,
        "discount_amount": 0,
        "tax_amount": 0,
        "delivery_amount": 0,
        "total_amount": 100,
    }
    values[field] = value

    with pytest.raises(ValidationError):
        await totals.update_order_totals(
            order_id=17,
            session=FakeSession(),
            **values,
        )


@pytest.mark.asyncio
async def test_update_totals_rejects_locked_order(monkeypatch):
    order = Order(
        status="completed",
        id=17,
        order_number="RST1-000017",
    )

    class OrdersRepository:
        def __init__(self, *, session):
            pass

        async def get_by_id(self, *, id):
            return order

    monkeypatch.setattr(totals, "OrdersRepository", OrdersRepository)

    with pytest.raises(ValueError):
        await totals.update_order_totals(
            order_id=17,
            subtotal_amount=100,
            discount_amount=0,
            tax_amount=0,
            delivery_amount=0,
            total_amount=100,
            session=FakeSession(),
        )


@pytest.mark.asyncio
async def test_read_orders_always_scopes_pagination_and_status_to_restaurant(monkeypatch):
    expected = [SimpleNamespace(id=17, restaurant_id=8)]
    calls = []

    class OrdersRepository:
        def __init__(self, *, session):
            pass

        async def get_by_restaurant_id(self, **kwargs):
            calls.append(kwargs)
            return expected

    monkeypatch.setattr(read, "OrdersRepository", OrdersRepository)

    result = await read.get_orders(
        restaurant_id=8,
        session=FakeSession(),
        skip=10,
        limit=5,
        status="pending",
    )

    assert result == expected
    assert calls == [{
        "restaurant_id": 8,
        "skip": 10,
        "limit": 5,
        "status": "pending",
    }]


@pytest.mark.asyncio
async def test_orders_repository_query_is_scoped_to_restaurant():
    expected = [SimpleNamespace(id=17, restaurant_id=8)]
    session = FakeSession()

    class Result:
        def scalars(self):
            return self

        def all(self):
            return expected

    async def execute(statement):
        session.statements.append(statement)
        return Result()

    session.execute = execute
    result = await OrdersRepository(session=session).get_by_restaurant_id(
        restaurant_id=8,
        status="pending",
    )

    statement = session.statements[0]
    compiled = statement.compile()
    assert result == expected
    assert "orders.restaurant_id" in str(compiled)
    assert 8 in compiled.params.values()


@pytest.mark.asyncio
async def test_customer_order_query_is_scoped_to_chat_and_locks_order():
    session = FakeSession(result=None)
    result = await customer_orders.get_customer_order(
        chat_id=425,
        order_reference="RST1-000017",
        session=session,
        lock=True,
    )

    statement = session.statements[0]
    compiled = statement.compile()
    assert result is None
    assert "users.chat_id" in str(compiled)
    assert 425 in compiled.params.values()
    assert statement._for_update_arg is not None


@pytest.mark.asyncio
async def test_get_orders_by_status_rejects_invalid_status_before_repository(monkeypatch):
    class UnexpectedRepository:
        def __init__(self, *, session):
            pytest.fail("Invalid status must be rejected before querying")

    monkeypatch.setattr(read, "OrdersRepository", UnexpectedRepository)

    with pytest.raises(ValueError):
        await read.get_orders_by_status(
            restaurant_id=8,
            status="unknown",
            session=FakeSession(),
        )


@pytest.mark.asyncio
async def test_cancel_order_locks_record_and_rejects_replay(monkeypatch):
    order = SimpleNamespace(
        id=17,
        status="pending",
        is_paid=False,
        order_number="RST1-000017",
    )
    session = FakeSession(result=order)
    transitions = []

    async def change_status(**kwargs):
        transitions.append(kwargs)
        order.status = "cancelled"
        return order

    monkeypatch.setattr(cancel, "change_order_status", change_status)

    await cancel.cancel_order(
        order_id=17,
        employee_id=5,
        reason="Customer request",
        session=session,
    )

    statement = session.statements[0]
    assert statement._for_update_arg is not None
    assert statement.compile().params["id_1"] == 17
    assert transitions[0]["note"] == "Customer request"
    assert session.transaction.committed is True

    replay_session = FakeSession(result=order)
    with pytest.raises(ValidationError, match="ملغى بالفعل"):
        await cancel.cancel_order(order_id=17, session=replay_session)

    assert replay_session.transaction.rolled_back is True
    assert transitions.__len__() == 1


@pytest.mark.asyncio
async def test_cancel_order_uses_savepoint_when_caller_owns_transaction(monkeypatch):
    order = SimpleNamespace(
        id=17,
        status="pending",
        is_paid=False,
        order_number="RST1-000017",
    )
    session = FakeSession(result=order, active_transaction=True)
    monkeypatch.setattr(cancel, "change_order_status", AsyncMock())

    await cancel.cancel_order(order_id=17, session=session)

    cancel.change_order_status.assert_awaited_once()
    assert session.commits == 0
    assert session.transaction.committed is True


@pytest.mark.asyncio
async def test_cancel_order_with_refund_requires_payment_and_delegates_cancellation(monkeypatch):
    from app.services.business.order_payments_service import OrderPaymentsService
    order = SimpleNamespace(is_paid=True, payments=[SimpleNamespace(id=42, payment_status="paid")])
    refund = AsyncMock()
    monkeypatch.setattr(OrderPaymentsService, "refund_payment", refund)
    monkeypatch.setattr(cancel, "cancel_order", AsyncMock())

    await cancel.cancel_order_with_refund(
        order_id=17,
        employee_id=5,
        reason="Customer request",
        session=FakeSession(result=order),
    )

    cancel.cancel_order.assert_awaited_once()
    assert cancel.cancel_order.await_args.kwargs["reason"] == "Customer request"

    refund.assert_awaited_once_with(payment_id=42)


@pytest.mark.asyncio
async def test_cancel_order_not_found_rolls_back(monkeypatch):
    session = FakeSession(result=None)
    monkeypatch.setattr(cancel, "change_order_status", AsyncMock())

    with pytest.raises(NotFoundError):
        await cancel.cancel_order(order_id=17, session=session)

    assert session.transaction.rolled_back is True
    cancel.change_order_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_status_history_timeline_uses_new_status_for_display(monkeypatch):
    async def get_timeline(*, order_id):
        return [
            {"new_status": "confirmed", "created_at": "timestamp"},
        ]

    class HistoryRepository:
        def __init__(self, *, session):
            pass

        async def get_status_timeline(self, *, order_id):
            return await get_timeline(order_id=order_id)

        async def get_last_status_change(self, *, order_id):
            return SimpleNamespace(
                new_status="confirmed",
                created_at="timestamp",
            )

    monkeypatch.setattr(status_history, "OrderStatusHistoryRepository", HistoryRepository)

    timeline = await status_history.get_order_timeline(order_id=17, session=object())
    latest = await status_history.get_last_status(order_id=17, session=object())

    assert timeline[0]["status_display"] != "unknown"
    assert timeline[0]["status_display"] == "✅ مؤكد"
    assert latest.new_status == "confirmed"


@pytest.mark.asyncio
async def test_status_history_reached_status_validates_and_returns_repository_result(monkeypatch):
    calls = []

    class HistoryRepository:
        def __init__(self, *, session):
            pass

        async def get_orders_reached_status(self, *, status):
            calls.append(status)
            return [17, 21]

    monkeypatch.setattr(status_history, "OrderStatusHistoryRepository", HistoryRepository)

    assert await status_history.get_orders_reached_status(
        status="ready",
        session=FakeSession(),
    ) == [17, 21]
    assert calls == ["ready"]

    with pytest.raises(ValidationError):
        await status_history.get_orders_reached_status(
            status="unknown",
            session=FakeSession(),
        )
