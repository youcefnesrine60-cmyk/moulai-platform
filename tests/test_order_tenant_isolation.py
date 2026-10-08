"""Execute isolation predicates against separate owners/restaurants in SQLite.

PostgreSQL locking/transaction integration is covered by the main suite.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import Column, MetaData, Table, create_engine
from sqlalchemy.pool import StaticPool

from app.api import auth
from app.api.v1 import orders
from app.models.order import Order
from app.models.restaurant import Restaurant
from app.models.user import User
from app.services.business.orders import customer
from app.core.exceptions import NotFoundError
import app.agent.executor.actions as actions


@pytest.fixture(autouse=True)
def cleanup_test_database():
    # This module owns an isolated in-memory database, never the shared DB.
    yield


@pytest.fixture
def isolated_session():
    engine = create_engine('sqlite://', poolclass=StaticPool,
                           connect_args={'check_same_thread': False})
    metadata = MetaData()
    tables = {}
    for model in (Restaurant, Order, User):
        tables[model] = Table(model.__tablename__, metadata, *[
            Column(c.name, c.type, nullable=True) for c in model.__table__.columns
        ])
    metadata.create_all(engine)
    connection = engine.connect()
    connection.execute(tables[Restaurant].insert(), [
        {'id': 10, 'owner_id': 1}, {'id': 20, 'owner_id': 2},
        {'id': 30, 'owner_id': 1},
    ])
    connection.execute(tables[User].insert(), [
        {'id': 7, 'chat_id': 700}, {'id': 8, 'chat_id': 800},
    ])
    connection.execute(tables[Order].insert(), [
        {'id': 100, 'restaurant_id': 10, 'user_id': 7,
         'order_number': 'RST10-1', 'status': 'pending'},
        {'id': 200, 'restaurant_id': 20, 'user_id': 7,
         'order_number': 'RST20-1', 'status': 'pending'},
        {'id': 300, 'restaurant_id': 30, 'user_id': 7,
         'order_number': 'RST30-1', 'status': 'pending'},
    ])

    class Session:
        def __init__(self):
            self.info = {}
            self.added = []
            self.flush = AsyncMock()

        async def execute(self, statement):
            result = connection.execute(statement)
            if statement.column_descriptions[0].get('entity') is Order and len(statement.selected_columns) > 1:
                row = result.mappings().first()
                value = SimpleNamespace(**row) if row else None
                return SimpleNamespace(scalar_one_or_none=lambda: value)
            return result

        def in_transaction(self):
            return False

        def begin(self):
            class Transaction:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    return False
            return Transaction()

        def add(self, value):
            self.added.append(value)

    session = Session()
    yield session
    connection.close()
    engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize('owner_id,order_id,allowed', [
    (1, 100, True), (2, 100, False), (1, 200, False), (2, 200, True),
])
async def test_order_owner_isolation_executes_sql(isolated_session, owner_id, order_id, allowed):
    if allowed:
        await auth.require_owned_order(order_id=order_id,
            owner=auth.OwnerPrincipal(owner_id), session=isolated_session)
    else:
        with pytest.raises(HTTPException) as error:
            await auth.require_owned_order(order_id=order_id,
                owner=auth.OwnerPrincipal(owner_id), session=isolated_session)
        assert error.value.status_code == 404


@pytest.mark.parametrize('method,path,payload', [
    ('get', '/orders/100', None),
    ('patch', '/orders/100', {'customer_note': 'intrusion'}),
    ('patch', '/orders/100/status', {'status': 'confirmed'}),
    ('post', '/orders/100/cancel', None),
    ('post', '/orders/100/complete', None),
    ('post', '/orders/100/paid?payment_id=1', None),
    ('delete', '/orders/100', None),
    ('get', '/orders/?restaurant_id=10', None),
    ('get', '/orders/stats/summary?restaurant_id=10', None),
])
def test_cross_tenant_http_operations_denied_before_service(isolated_session, method, path, payload):
    app = FastAPI()
    app.include_router(orders.router)
    service = SimpleNamespace(session=isolated_session)
    app.dependency_overrides[auth.get_current_owner] = lambda: auth.OwnerPrincipal(2)
    app.dependency_overrides[orders.get_order_service] = lambda: service
    app.dependency_overrides[orders.get_order_items_service] = lambda: service
    # No service methods exist: calling one would produce 500 instead of 404.
    with TestClient(app) as client:
        response = client.request(method, path, json=payload)
    assert response.status_code == 404
    assert isolated_session.added == []
    isolated_session.flush.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('chat_id,restaurant_id,allowed', [
    (700, 10, True), (800, 10, False), (700, 20, False),
    (700, 30, False),
])
async def test_customer_tracking_is_bound_to_customer_and_restaurant(isolated_session, chat_id, restaurant_id, allowed):
    order = await customer.get_customer_order(chat_id=chat_id,
        restaurant_id=restaurant_id, order_reference='100', session=isolated_session)
    assert (order is not None) is allowed


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['cancel', 'modify'])
@pytest.mark.parametrize('chat_id,restaurant_id', [(800, 10), (700, 20), (700, 30)])
async def test_cross_customer_or_restaurant_mutations_have_no_side_effects(isolated_session, operation, chat_id, restaurant_id):
    kwargs = dict(chat_id=chat_id, restaurant_id=restaurant_id,
                  order_reference=100, session=isolated_session)
    with pytest.raises(NotFoundError):
        if operation == 'cancel':
            await customer.cancel_customer_order(**kwargs, reason='intrusion')
        else:
            await customer.change_customer_order_item_quantity(**kwargs,
                product_name='Pizza', quantity=2)
    assert isolated_session.added == []
    isolated_session.flush.assert_not_awaited()
    order = await customer.get_customer_order(chat_id=700, restaurant_id=10,
        order_reference=100, session=isolated_session)
    assert order.status == 'pending'


@pytest.mark.asyncio
@pytest.mark.parametrize('action_type,service_name', [
    (actions.TrackOrderAction, 'get_customer_order'),
    (actions.CancelOrderAction, 'cancel_customer_order'),
    (actions.ModifyOrderAction, 'change_customer_order_item_quantity'),
])
async def test_actions_preserve_channel_restaurant_over_extracted_entity(monkeypatch, action_type, service_name):
    class Session:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
    monkeypatch.setattr(actions, 'AsyncSessionLocal', Session)
    service = AsyncMock(side_effect=NotFoundError(message='not found'))
    monkeypatch.setattr(actions, service_name, service)
    if action_type is actions.TrackOrderAction:
        service.side_effect = None
        service.return_value = None
    result = await action_type().execute(
        params={'order_id': 100, 'restaurant_id': 10, 'quantity': 2},
        context={'user_id': 700, 'request_context': {'restaurant_id': 20}})
    assert result.success is False
    assert service.await_args.kwargs['restaurant_id'] == 20
