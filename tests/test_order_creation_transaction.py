from types import SimpleNamespace

import pytest

from app.core.exceptions import ValidationError
from app.services.business.orders import create as order_creation


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


class FakeSession:
    def __init__(self, *, active_transaction=False):
        self.info = {}
        self.active_transaction = active_transaction
        self.transaction = FakeTransaction()
        self.outer_commits = 0

    def get_transaction(self):
        return SimpleNamespace(sync_transaction=SimpleNamespace(origin=None))

    async def flush(self):
        pass

    def in_transaction(self):
        return self.active_transaction

    def begin(self):
        return self.transaction

    def begin_nested(self):
        return self.transaction

    async def commit(self):
        self.outer_commits += 1


def order_arguments(session):
    return {
        "restaurant_id": 3,
        "branch_id": None,
        "table_id": None,
        "employee_id": None,
        "user_id": 12,
        "order_type": "takeaway",
        "customer_name": None,
        "customer_phone": None,
        "delivery_address": None,
        "customer_note": None,
        "subtotal_amount": 850.0,
        "discount_amount": 0.0,
        "tax_amount": 0.0,
        "delivery_amount": 0.0,
        "total_amount": 850.0,
        "items": [{"product_id": 7, "quantity": 1}],
        "session": session,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("active_transaction", [False, True])
async def test_order_creation_uses_one_transaction_and_restores_session_mode(
    monkeypatch,
    active_transaction,
):
    session = FakeSession(active_transaction=active_transaction)

    async def create_order(**kwargs):
        assert kwargs["session"].info["defer_repository_commit"] is True
        return 91

    monkeypatch.setattr(
        order_creation,
        "_create_order_with_items_in_transaction",
        create_order,
    )

    order_id = await order_creation.create_order_with_items(
        **order_arguments(session),
    )

    assert order_id == 91
    assert session.transaction.committed is True
    assert session.transaction.rolled_back is False
    assert session.outer_commits == 0
    assert session.info == {}


@pytest.mark.asyncio
async def test_order_creation_rolls_back_and_restores_existing_session_mode(monkeypatch):
    session = FakeSession(active_transaction=True)
    session.info["defer_repository_commit"] = False

    async def fail_order_creation(**kwargs):
        raise RuntimeError("write failed")

    monkeypatch.setattr(
        order_creation,
        "_create_order_with_items_in_transaction",
        fail_order_creation,
    )

    with pytest.raises(RuntimeError, match="write failed"):
        await order_creation.create_order_with_items(
            **order_arguments(session),
        )

    assert session.transaction.rolled_back is True
    assert session.outer_commits == 0
    assert session.info["defer_repository_commit"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("active_transaction", [False, True])
async def test_restaurant_order_creation_generates_number_and_is_transactional(
    monkeypatch,
    active_transaction,
):
    session = FakeSession(active_transaction=active_transaction)

    class Result:
        def scalar_one_or_none(self):
            return object()

    async def execute(statement):
        return Result()

    session.execute = execute

    class CounterRepository:
        def __init__(self, *, session):
            self.session = session

        async def get_by_restaurant_id(self, *, restaurant_id):
            return None

        async def create_counter(self, *, restaurant_id):
            return None

        async def generate_next_order_number(self, *, restaurant_id):
            return f"RST{restaurant_id}-000001"

    async def create_order(**kwargs):
        assert kwargs["order_number"] == "RST3-000001"
        assert kwargs["session"].info["defer_repository_commit"] is True
        return 72

    monkeypatch.setattr(order_creation, "RestaurantOrderCountersRepository", CounterRepository)
    monkeypatch.setattr(order_creation, "_create_restaurant_order_in_transaction", create_order)

    order_id = await order_creation.create_restaurant_order(
        restaurant_id=3,
        branch_id=None,
        table_id=None,
        employee_id=None,
        order_number="",
        order_type="takeaway",
        customer_name=None,
        customer_phone=None,
        delivery_address=None,
        customer_note=None,
        session=session,
    )

    assert order_id == 72
    assert session.transaction.committed is True
    assert session.outer_commits == 0
    assert session.info == {}


@pytest.mark.asyncio
async def test_create_order_with_items_writes_order_item_history_and_metrics_atomically(monkeypatch):
    session = FakeSession()
    session.statements = []

    async def execute(statement):
        session.statements.append(statement)
        return await _restaurant_result()

    session.execute = execute
    writes = {"orders": [], "items": [], "options": [], "history": [], "metrics": [], "usage": []}

    class OrdersRepository:
        def __init__(self, *, session):
            pass

        async def create(self, *, data):
            writes["orders"].append(data.copy())
            return SimpleNamespace(id=91, order_number=data["order_number"])

    class ItemsRepository:
        def __init__(self, *, session):
            pass

        async def create(self, *, data):
            writes["items"].append(data.copy())
            return SimpleNamespace(id=101)

    class OptionsRepository:
        def __init__(self, *, session):
            pass

        async def create(self, *, data):
            writes["options"].append(data.copy())
            return data

    class HistoryRepository:
        def __init__(self, *, session):
            pass

        async def create(self, *, data):
            writes["history"].append(data.copy())
            return data

    class CounterRepository:
        def __init__(self, *, session):
            pass

        async def get_by_restaurant_id(self, *, restaurant_id):
            return SimpleNamespace(last_number=0)

        async def generate_next_order_number(self, *, restaurant_id):
            return "RST3-000001"

    class MetricsRepository:
        def __init__(self, *, session):
            pass

        async def get_by_restaurant_id(self, *, restaurant_id):
            return None

        async def create(self, *, data):
            writes["metrics"].append(data.copy())
            return data

    async def increase_usage(**kwargs):
        writes["usage"].append(kwargs)

    monkeypatch.setattr(order_creation, "OrdersRepository", OrdersRepository)
    monkeypatch.setattr(order_creation, "OrderItemsRepository", ItemsRepository)
    monkeypatch.setattr(order_creation, "OrderItemOptionsRepository", OptionsRepository)
    monkeypatch.setattr(order_creation, "OrderStatusHistoryRepository", HistoryRepository)
    monkeypatch.setattr(order_creation, "RestaurantOrderCountersRepository", CounterRepository)
    monkeypatch.setattr(order_creation, "RestaurantMetricsRepository", MetricsRepository)
    monkeypatch.setattr(order_creation, "increase_usage", increase_usage)

    order_id = await order_creation.create_order_with_items(
        restaurant_id=3,
        branch_id=None,
        table_id=None,
        employee_id=5,
        user_id=12,
        order_type="takeaway",
        customer_name=None,
        customer_phone=None,
        delivery_address=None,
        customer_note=None,
        subtotal_amount=25.0,
        discount_amount=0.0,
        tax_amount=0.0,
        delivery_amount=0.0,
        total_amount=25.0,
        items=[{
            "product_id": 7,
            "product_name": "Pizza",
            "unit_price": 25.0,
            "quantity": 1,
            "total_price": 25.0,
            "options": [{
                "option_group_name": "Crust",
                "option_name": "Thin",
                "additional_price": 0.0,
            }],
        }],
        session=session,
    )

    assert order_id == 91
    assert writes["orders"][0]["user_id"] == 12
    assert writes["orders"][0]["restaurant_id"] == 3
    assert writes["items"][0]["order_id"] == 91
    assert writes["options"][0]["order_item_id"] == 101
    assert writes["history"][0]["old_status"] is None
    assert writes["history"][0]["new_status"] == "pending"
    assert writes["metrics"][0]["monthly_orders"] == 1
    assert writes["usage"][0]["restaurant_id"] == 3
    assert session.transaction.committed is True
    restaurant_query = session.statements[0]
    assert "restaurants.id" in str(restaurant_query.compile())
    assert 3 in restaurant_query.compile().params.values()


@pytest.mark.asyncio
async def test_create_order_with_items_rolls_back_partial_order_when_item_is_invalid(monkeypatch):
    session = FakeSession()
    session.execute = lambda statement: _restaurant_result()
    created_orders = []

    class OrdersRepository:
        def __init__(self, *, session):
            pass

        async def create(self, *, data):
            created_orders.append(data)
            return SimpleNamespace(id=91)

    class CounterRepository:
        def __init__(self, *, session):
            pass

        async def get_by_restaurant_id(self, *, restaurant_id):
            return SimpleNamespace(last_number=0)

        async def generate_next_order_number(self, *, restaurant_id):
            return "RST3-000001"

    monkeypatch.setattr(order_creation, "OrdersRepository", OrdersRepository)
    monkeypatch.setattr(order_creation, "RestaurantOrderCountersRepository", CounterRepository)

    with pytest.raises(ValidationError, match="معرف المنتج مطلوب"):
        await order_creation.create_order_with_items(
            restaurant_id=3,
            branch_id=None,
            table_id=None,
            employee_id=None,
            order_type="takeaway",
            customer_name=None,
            customer_phone=None,
            delivery_address=None,
            customer_note=None,
            subtotal_amount=25.0,
            discount_amount=0.0,
            tax_amount=0.0,
            delivery_amount=0.0,
            total_amount=25.0,
            items=[{"product_id": None, "quantity": 1}],
            session=session,
        )

    assert len(created_orders) == 0  # Validate catalog items before writes.
    assert session.transaction.rolled_back is True
    assert session.info == {}


async def _restaurant_result():
    class Result:
        def scalar_one_or_none(self):
            return SimpleNamespace(id=3)

    return Result()


@pytest.fixture(autouse=True)
def catalog_for_aggregate_unit_tests(monkeypatch):
    async def catalog_item(*, payload, **kwargs):
        if not payload.get("product_id"):
            raise ValidationError(message="\u0645\u0639\u0631\u0641 \u0627\u0644\u0645\u0646\u062a\u062c \u0645\u0637\u0644\u0648\u0628")
        return payload.copy()
    monkeypatch.setattr(order_creation, "catalog_item", catalog_item)


@pytest.fixture(autouse=True)
def item_workflow_for_aggregate_unit_tests(monkeypatch):
    async def add_item(*, order_id, session, **payload):
        values = dict(payload)
        options = values.pop("options", [])
        item = await order_creation.OrderItemsRepository(session=session).create(
            data=dict(values, order_id=order_id))
        for option in options:
            await order_creation.OrderItemOptionsRepository(session=session).create(
                data=dict(option, order_item_id=item.id))
        return item
    monkeypatch.setattr(order_creation, "add_item_to_order", add_item)
