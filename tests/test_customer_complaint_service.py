from types import SimpleNamespace

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.models.complaint import Complaint
from app.services.business.complaints import create_customer_complaint


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


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
    def __init__(self, *, order=None):
        self.user = SimpleNamespace(id=7, chat_id=55, consent=True)
        self.order = order
        self.restaurant = SimpleNamespace(id=8)
        self.transaction = FakeTransaction()
        self.added = []
        self.execute_calls = 0

    def begin(self):
        return self.transaction

    async def execute(self, statement):
        self.execute_calls += 1
        value = self.user if self.execute_calls == 1 else self.order
        return FakeResult(value)

    async def get(self, model, entity_id):
        return self.restaurant if entity_id == 8 else None

    def add(self, instance):
        instance.id = 36
        self.added.append(instance)

    async def flush(self):
        return None


@pytest.mark.asyncio
async def test_creates_open_complaint_for_customer_and_restaurant():
    session = FakeSession()

    complaint = await create_customer_complaint(
        chat_id=55,
        restaurant_id=8,
        order_reference=None,
        description="  The food arrived cold.  ",
        session=session,
    )

    assert isinstance(complaint, Complaint)
    assert complaint.id == 36
    assert complaint.user_id == 7
    assert complaint.restaurant_id == 8
    assert complaint.order_id is None
    assert complaint.description == "The food arrived cold."
    assert complaint.status == "open"
    assert session.transaction.committed is True


@pytest.mark.asyncio
async def test_order_reference_links_only_customer_owned_order():
    order = SimpleNamespace(id=91, restaurant_id=8)
    session = FakeSession(order=order)

    complaint = await create_customer_complaint(
        chat_id=55,
        restaurant_id=None,
        order_reference="RST8-000091",
        description="The order was incomplete.",
        session=session,
    )

    assert complaint.order_id == 91
    assert complaint.restaurant_id == 8
    assert session.transaction.committed is True


@pytest.mark.asyncio
async def test_rejects_order_from_a_different_restaurant_atomically():
    session = FakeSession(order=SimpleNamespace(id=91, restaurant_id=9))

    with pytest.raises(ValidationError) as error:
        await create_customer_complaint(
            chat_id=55,
            restaurant_id=8,
            order_reference="RST9-000091",
            description="The order was incomplete.",
            session=session,
        )

    assert error.value.error_code == "COMPLAINT_ORDER_RESTAURANT_MISMATCH"
    assert session.added == []
    assert session.transaction.rolled_back is True


@pytest.mark.asyncio
async def test_rejects_order_not_owned_by_customer():
    session = FakeSession(order=None)

    with pytest.raises(NotFoundError) as error:
        await create_customer_complaint(
            chat_id=55,
            restaurant_id=8,
            order_reference="RST8-000091",
            description="The order was incomplete.",
            session=session,
        )

    assert error.value.error_code == "ORDER_NOT_FOUND"
    assert session.added == []
    assert session.transaction.rolled_back is True
