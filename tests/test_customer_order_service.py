from types import SimpleNamespace

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.models.order_item import OrderStatusHistory
from app.services.business.orders.customer import (
    cancel_customer_order,
    change_customer_order_item_quantity,
)


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


class ListResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, query_results):
        self.info = {}
        self.query_results = iter(query_results)
        self.transaction = FakeTransaction()
        self.added = []

    def begin(self):
        return self.transaction

    def in_transaction(self):
        return False

    async def execute(self, statement):
        return next(self.query_results)

    def add(self, instance):
        self.added.append(instance)

    async def flush(self):
        return None


@pytest.mark.asyncio
async def test_modify_customer_order_quantity_recalculates_totals_atomically():
    order = SimpleNamespace(
        id=17,
        order_number="RST1-000017",
        status="pending",
        discount_amount=10.0,
        tax_amount=5.0,
        delivery_amount=20.0,
        subtotal_amount=200.0,
        total_amount=215.0,
    )
    item = SimpleNamespace(
        id=21,
        order_id=17,
        product_name="Pizza",
        unit_price=100.0,
        quantity=2,
        total_price=200.0,
    )
    session = FakeSession([ScalarResult(order), ListResult([item])])

    updated_order, updated_item = await change_customer_order_item_quantity(
        chat_id=425,
        order_reference=order.order_number,
        product_name="pizza",
        quantity=3,
        session=session,
    )

    assert updated_order is order
    assert updated_item is item
    assert item.quantity == 3
    assert item.total_price == 300.0
    assert order.subtotal_amount == 300.0
    assert order.total_amount == 315.0
    assert session.transaction.committed is True


@pytest.mark.asyncio
async def test_modify_customer_order_rejects_non_pending_order():
    order = SimpleNamespace(id=17, status="confirmed", items=[])
    session = FakeSession([ScalarResult(order)])

    with pytest.raises(ValidationError) as exc_info:
        await change_customer_order_item_quantity(
            chat_id=425,
            order_reference="RST1-000017",
            product_name="Pizza",
            quantity=3,
            session=session,
        )

    assert exc_info.value.error_code == "ORDER_NOT_MODIFIABLE"
    assert session.transaction.rolled_back is True


@pytest.mark.asyncio
async def test_customer_order_modification_cannot_access_another_customer_order():
    session = FakeSession([ScalarResult(None)])

    with pytest.raises(NotFoundError) as exc_info:
        await change_customer_order_item_quantity(
            chat_id=425,
            order_reference="RST1-000017",
            product_name="Pizza",
            quantity=3,
            session=session,
        )

    assert exc_info.value.error_code == "ORDER_NOT_FOUND"
    assert session.transaction.rolled_back is True


@pytest.mark.asyncio
async def test_customer_cancellation_updates_status_and_history_atomically():
    order = SimpleNamespace(id=17, order_number="RST1-000017", status="pending")
    session = FakeSession([ScalarResult(order)])

    cancelled_order, previous_status = await cancel_customer_order(
        chat_id=425,
        order_reference=order.order_number,
        reason="Duplicate",
        session=session,
    )

    assert cancelled_order is order
    assert previous_status == "pending"
    assert order.status == "cancelled"
    assert len(session.added) == 1
    assert isinstance(session.added[0], OrderStatusHistory)
    assert session.added[0].old_status == "pending"
    assert session.added[0].new_status == "cancelled"
    assert session.transaction.committed is True


@pytest.mark.asyncio
async def test_customer_cancellation_replay_is_rejected_without_duplicate_history():
    order = SimpleNamespace(id=17, order_number="RST1-000017", status="cancelled")
    session = FakeSession([ScalarResult(order)])

    with pytest.raises(ValidationError) as exc_info:
        await cancel_customer_order(
            chat_id=425,
            order_reference=order.order_number,
            reason="Retry",
            session=session,
        )

    assert exc_info.value.error_code == "ORDER_NOT_CANCELLABLE"
    assert session.added == []
    assert session.transaction.rolled_back is True


@pytest.mark.asyncio
async def test_replaying_same_quantity_change_does_not_double_charge():
    order = SimpleNamespace(
        id=17,
        order_number="RST1-000017",
        status="pending",
        discount_amount=0.0,
        tax_amount=0.0,
        delivery_amount=0.0,
        subtotal_amount=100.0,
        total_amount=100.0,
    )
    item = SimpleNamespace(
        id=21,
        order_id=17,
        product_name="Pizza",
        unit_price=50.0,
        quantity=2,
        total_price=100.0,
    )

    for _ in range(2):
        session = FakeSession([ScalarResult(order), ListResult([item])])
        await change_customer_order_item_quantity(
            chat_id=425,
            order_reference=order.order_number,
            product_name="Pizza",
            quantity=3,
            session=session,
        )
        assert session.transaction.committed is True

    assert item.quantity == 3
    assert item.total_price == 150.0
    assert order.total_amount == 150.0


@pytest.fixture(autouse=True)
def append_history_to_fake_session(monkeypatch):
    from app.repositories.order_status_history_repo import OrderStatusHistoryRepository
    async def create(self, *, data):
        record = OrderStatusHistory(**data)
        self.session.add(record)
        await self.session.flush()
        return record
    monkeypatch.setattr(OrderStatusHistoryRepository, "create", create)
