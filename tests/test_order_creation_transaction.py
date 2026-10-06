import pytest

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
async def test_order_creation_uses_one_transaction_and_restores_session_mode(monkeypatch):
    session = FakeSession()

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
async def test_restaurant_order_creation_generates_number_and_is_transactional(monkeypatch):
    session = FakeSession()

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
    assert session.info == {}
