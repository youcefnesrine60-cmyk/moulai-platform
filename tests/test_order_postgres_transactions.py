# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# TEST MODULE - TESTS / TEST ORDER POSTGRES TRANSACTIONS
# Automated test coverage for the MoulAI platform.
# ==============================================

"""PostgreSQL proofs: real commits, rollback, API authorization and catalog scope."""

from types import SimpleNamespace

import pytest
from sqlalchemy import insert, select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api import auth
from app.main import app
from app.models.owner import Owner
from app.models.restaurant import Restaurant
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.models.order import Order
from app.models.order_item import OrderItem, OrderPayment, OrderStatusHistory
from app.models.subscription import Feature
from app.models.restaurant_order_counter import RestaurantOrderCounter
from app.models.feature_pricing import FeatureUsageCounter
from app.repositories.orders_repo import OrdersRepository
from app.repositories.order_items_repo import OrderItemsRepository
from app.repositories.order_status_history_repo import OrderStatusHistoryRepository
from app.services.business.orders.transaction import order_transaction
from app.services.business.orders import create
from app.services.business.order_items_service import OrderItemsService

# ==============================================
# ORDER GRAPH
# ==============================================


@pytest.fixture
async def order_graph(db_session, sample_restaurant_data):
    # ==============================================
    # PUT
    # ==============================================

    async def put(model, **values):
        return (
            await db_session.execute(
                insert(model.__table__).values(**values).returning(model.id)
            )
        ).scalar_one()

    owner_a = await put(Owner, chat_id=71001, full_name="Owner A")
    owner_b = await put(Owner, chat_id=71002, full_name="Owner B")
    restaurant_a = await put(
        Restaurant, **dict(sample_restaurant_data, owner_id=owner_a, name="A")
    )
    restaurant_b = await put(
        Restaurant, **dict(sample_restaurant_data, owner_id=owner_b, name="B")
    )
    user = await put(User, chat_id=72001, consent=True)
    category_a = await put(Category, restaurant_id=restaurant_a, name="A")
    category_b = await put(Category, restaurant_id=restaurant_b, name="B")
    product_a = await put(
        Product,
        restaurant_id=restaurant_a,
        category_id=category_a,
        name="Pizza",
        price=25,
        is_available=True,
    )
    product_b = await put(
        Product,
        restaurant_id=restaurant_b,
        category_id=category_b,
        name="Other pizza",
        price=40,
        is_available=True,
    )
    order_a = await put(
        Order,
        restaurant_id=restaurant_a,
        user_id=user,
        order_number="BASE-A",
        order_type="takeaway",
        status="pending",
        subtotal_amount=25,
        total_amount=25,
    )
    order_b = await put(
        Order,
        restaurant_id=restaurant_b,
        user_id=user,
        order_number="BASE-B",
        order_type="takeaway",
        status="pending",
        subtotal_amount=40,
        total_amount=40,
    )
    item_a = await put(
        OrderItem,
        order_id=order_a,
        product_id=product_a,
        product_name="Pizza",
        unit_price=25,
        quantity=1,
        total_price=25,
    )
    payment_a = await put(
        OrderPayment,
        order_id=order_a,
        payment_method="cash",
        payment_status="pending",
        amount=25,
    )
    payment_b = await put(
        OrderPayment,
        order_id=order_b,
        payment_method="cash",
        payment_status="pending",
        amount=40,
    )
    await put(Feature, id=6, code="orders", name="Orders")
    await db_session.commit()
    sessions = async_sessionmaker(
        db_session.bind, class_=AsyncSession, expire_on_commit=False
    )
    return SimpleNamespace(**locals())


# ==============================================
# SCALAR FROM NEW SESSION
# ==============================================


async def scalar_from_new_session(graph, statement):
    async with graph.sessions() as reader:
        return (await reader.execute(statement)).scalar_one()


# ==============================================
# PAYLOAD
# ==============================================


def payload(graph, product_id=None):
    return dict(
        restaurant_id=graph.restaurant_a,
        order_type="takeaway",
        items=[
            dict(
                product_id=product_id or graph.product_a,
                product_name="Untrusted name",
                unit_price=0.01,
                quantity=2,
                total_price=0.02,
            )
        ],
    )


# ==============================================
# OWNER CLIENT
# ==============================================


@pytest.fixture
async def owner_client(client, order_graph):
    app.dependency_overrides[auth.get_current_owner] = lambda: auth.OwnerPrincipal(
        order_graph.owner_a
    )
    yield client
    app.dependency_overrides.pop(auth.get_current_owner, None)


# ==============================================
# TEST POSTGRES AUTOBEGIN COMMIT AND EXPLICIT OUTER ROLLBACK
# ==============================================


@pytest.mark.asyncio
async def test_postgres_autobegin_commit_and_explicit_outer_rollback(order_graph):
    g = order_graph
    async with g.sessions() as writer:
        # Like an API authorization query, this opens an implicit transaction.
        await auth.require_owned_order(
            order_id=g.order_a, owner=auth.OwnerPrincipal(g.owner_a), session=writer
        )
        async with order_transaction(writer):
            await OrdersRepository(session=writer).update(
                id=g.order_a, data={"customer_note": "persisted"}
            )
    assert (
        await scalar_from_new_session(
            g, select(Order.customer_note).where(Order.id == g.order_a)
        )
        == "persisted"
    )
    async with g.sessions() as writer:
        await writer.begin()
        async with order_transaction(writer):
            await OrdersRepository(session=writer).update(
                id=g.order_a, data={"customer_note": "caller owned"}
            )
        assert (
            await scalar_from_new_session(
                g, select(Order.customer_note).where(Order.id == g.order_a)
            )
            == "persisted"
        )
        with pytest.raises(RuntimeError):
            async with order_transaction(writer):
                await OrdersRepository(session=writer).update(
                    id=g.order_a, data={"customer_note": "nested failure"}
                )
                raise RuntimeError("child failure")
        assert writer.in_transaction()
        await writer.rollback()
    assert (
        await scalar_from_new_session(
            g, select(Order.customer_note).where(Order.id == g.order_a)
        )
        == "persisted"
    )
    async with g.sessions() as writer:
        await writer.execute(select(Order.id))
        with pytest.raises(RuntimeError):
            async with order_transaction(writer):
                await OrdersRepository(session=writer).update(
                    id=g.order_a, data={"customer_note": "failed"}
                )
                raise RuntimeError("injected failure")
    assert (
        await scalar_from_new_session(
            g, select(Order.customer_note).where(Order.id == g.order_a)
        )
        == "persisted"
    )


# ==============================================
# TEST POSTGRES API CREATION PERSISTS CATALOG PRICES
# ==============================================


@pytest.mark.asyncio
async def test_postgres_api_creation_persists_catalog_prices(owner_client, order_graph):
    g = order_graph
    response = await owner_client.post("/api/v1/orders/", json=payload(g))
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["total_amount"] == 50
    assert result["payment_status"] is None
    detail = await owner_client.get(f"/api/v1/orders/{result['id']}")
    assert detail.status_code == 200, detail.text
    assert len(detail.json()["items"]) == 1
    assert (
        await scalar_from_new_session(
            g, select(Order.total_amount).where(Order.id == result["id"])
        )
        == 50
    )
    assert (
        await scalar_from_new_session(
            g, select(OrderItem.unit_price).where(OrderItem.order_id == result["id"])
        )
        == 25
    )
    assert (
        await scalar_from_new_session(
            g,
            select(OrderStatusHistory.new_status).where(
                OrderStatusHistory.order_id == result["id"]
            ),
        )
        == "pending"
    )


# ==============================================
# TEST POSTGRES CREATION FAILURE ROLLS BACK EVERY WRITE
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["item", "history", "metrics", "usage"])
async def test_postgres_creation_failure_rolls_back_every_write(
    owner_client, order_graph, monkeypatch, stage
):
    g = order_graph
    if stage in {"item", "history"}:
        repository = (
            OrderItemsRepository if stage == "item" else OrderStatusHistoryRepository
        )
        original = repository.create

        # ==============================================
        # FAIL AFTER WRITE
        # ==============================================

        async def fail_after_write(self, **kwargs):
            await original(self, **kwargs)
            raise RuntimeError("injected after write")

        monkeypatch.setattr(repository, "create", fail_after_write)
    else:
        name = "_update_restaurant_metrics" if stage == "metrics" else "increase_usage"
        original = getattr(create, name)

        # ==============================================
        # FAIL AFTER WRITE
        # ==============================================

        async def fail_after_write(**kwargs):
            await original(**kwargs)
            raise RuntimeError("injected after write")

        monkeypatch.setattr(create, name, fail_after_write)
    response = await owner_client.post("/api/v1/orders/", json=payload(g))
    assert response.status_code == 500
    for model, expected in [
        (Order, 2),
        (OrderItem, 1),
        (OrderStatusHistory, 0),
        (RestaurantOrderCounter, 0),
        (FeatureUsageCounter, 0),
    ]:
        assert (
            await scalar_from_new_session(g, select(func.count()).select_from(model))
            == expected
        )


# ==============================================
# TEST POSTGRES CROSS RESTAURANT PRODUCT IS REJECTED WITHOUT ORDER
# ==============================================


@pytest.mark.asyncio
async def test_postgres_cross_restaurant_product_is_rejected_without_order(
    owner_client, order_graph
):
    response = await owner_client.post(
        "/api/v1/orders/", json=payload(order_graph, order_graph.product_b)
    )
    assert response.status_code == 404
    assert (
        await scalar_from_new_session(
            order_graph, select(func.count()).select_from(Order)
        )
        == 2
    )


# ==============================================
# TEST POSTGRES AUTHORIZED STATUS CHANGE IS PERSISTENT
# ==============================================


@pytest.mark.asyncio
async def test_postgres_authorized_status_change_is_persistent(
    owner_client, order_graph
):
    g = order_graph
    response = await owner_client.patch(
        f"/api/v1/orders/{g.order_a}/status", json={"status": "confirmed"}
    )
    assert response.status_code == 200, response.text
    assert (
        await scalar_from_new_session(
            g, select(Order.status).where(Order.id == g.order_a)
        )
        == "confirmed"
    )
    assert (
        await scalar_from_new_session(
            g,
            select(OrderStatusHistory.new_status).where(
                OrderStatusHistory.order_id == g.order_a
            ),
        )
        == "confirmed"
    )


# ==============================================
# TEST POSTGRES PAYMENT IS IDEMPOTENT AND KEEPS FULFILLMENT STATUS
# ==============================================


@pytest.mark.asyncio
async def test_postgres_payment_is_idempotent_and_keeps_fulfillment_status(
    owner_client, order_graph
):
    g = order_graph
    for _ in range(2):
        response = await owner_client.post(
            f"/api/v1/orders/{g.order_a}/paid", params={"payment_id": g.payment_a}
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "pending"
        assert response.json()["is_paid"] is True
    assert (
        await scalar_from_new_session(
            g, select(OrderPayment.payment_status).where(OrderPayment.id == g.payment_a)
        )
        == "paid"
    )
    assert (
        await scalar_from_new_session(
            g, select(func.count()).select_from(OrderStatusHistory)
        )
        == 0
    )
    response = await owner_client.post(
        f"/api/v1/orders/{g.order_a}/paid", params={"payment_id": g.payment_b}
    )
    assert response.status_code == 422
    assert (
        await scalar_from_new_session(
            g, select(OrderPayment.payment_status).where(OrderPayment.id == g.payment_b)
        )
        == "pending"
    )


# ==============================================
# TEST POSTGRES PAYMENT FAILURE ROLLS BACK PERSISTED PAYMENT
# ==============================================


@pytest.mark.asyncio
async def test_postgres_payment_failure_rolls_back_persisted_payment(
    owner_client, order_graph, monkeypatch
):
    from app.repositories.order_payments_repo import OrderPaymentsRepository

    original = OrderPaymentsRepository.mark_paid

    # ==============================================
    # FAIL AFTER WRITE
    # ==============================================

    async def fail_after_write(self, **kwargs):
        await original(self, **kwargs)
        raise RuntimeError("injected payment failure")

    monkeypatch.setattr(OrderPaymentsRepository, "mark_paid", fail_after_write)
    g = order_graph
    response = await owner_client.post(
        f"/api/v1/orders/{g.order_a}/paid", params={"payment_id": g.payment_a}
    )
    assert response.status_code == 500
    assert (
        await scalar_from_new_session(
            g, select(OrderPayment.payment_status).where(OrderPayment.id == g.payment_a)
        )
        == "pending"
    )
    assert (
        await scalar_from_new_session(
            g, select(Order.status).where(Order.id == g.order_a)
        )
        == "pending"
    )


# ==============================================
# TEST POSTGRES ITEM QUANTITY AND TOTAL COMMIT TOGETHER
# ==============================================


@pytest.mark.asyncio
async def test_postgres_item_quantity_and_total_commit_together(order_graph):
    g = order_graph
    async with g.sessions() as writer:
        await auth.require_owned_order(
            order_id=g.order_a, owner=auth.OwnerPrincipal(g.owner_a), session=writer
        )
        await OrderItemsService(writer).update_quantity(
            order_item_id=g.item_a, quantity=3
        )
    assert (
        await scalar_from_new_session(
            g, select(OrderItem.quantity).where(OrderItem.id == g.item_a)
        )
        == 3
    )
    assert (
        await scalar_from_new_session(
            g, select(Order.total_amount).where(Order.id == g.order_a)
        )
        == 75
    )


# ==============================================
# TEST POSTGRES STATUS HISTORY FAILURE ROLLS BACK ORDER
# ==============================================


@pytest.mark.asyncio
async def test_postgres_status_history_failure_rolls_back_order(
    owner_client, order_graph, monkeypatch
):
    original = OrderStatusHistoryRepository.create

    # ==============================================
    # FAIL AFTER WRITE
    # ==============================================

    async def fail_after_write(self, **kwargs):
        await original(self, **kwargs)
        raise RuntimeError("injected history failure")

    monkeypatch.setattr(OrderStatusHistoryRepository, "create", fail_after_write)
    g = order_graph
    response = await owner_client.patch(
        f"/api/v1/orders/{g.order_a}/status", json={"status": "confirmed"}
    )
    assert response.status_code == 500
    assert (
        await scalar_from_new_session(
            g, select(Order.status).where(Order.id == g.order_a)
        )
        == "pending"
    )
    assert (
        await scalar_from_new_session(
            g, select(func.count()).select_from(OrderStatusHistory)
        )
        == 0
    )


# ==============================================
# TEST POSTGRES CROSS OWNER API OPERATIONS LEAVE ORDER UNCHANGED
# ==============================================


@pytest.mark.asyncio
async def test_postgres_cross_owner_api_operations_leave_order_unchanged(
    owner_client, order_graph
):
    g = order_graph
    for method, suffix, data in [
        ("GET", "", None),
        ("PATCH", "", {"customer_note": "intrusion"}),
        ("PATCH", "/status", {"status": "confirmed"}),
        ("POST", "/cancel", None),
        ("DELETE", "", None),
        ("POST", f"/paid?payment_id={g.payment_b}", None),
    ]:
        response = await owner_client.request(
            method, f"/api/v1/orders/{g.order_b}{suffix}", json=data
        )
        assert response.status_code == 404
    assert (
        await scalar_from_new_session(
            g, select(Order.status).where(Order.id == g.order_b)
        )
        == "pending"
    )
    assert (
        await scalar_from_new_session(
            g, select(OrderPayment.payment_status).where(OrderPayment.id == g.payment_b)
        )
        == "pending"
    )
    assert (
        await scalar_from_new_session(
            g, select(func.count()).select_from(OrderStatusHistory)
        )
        == 0
    )


# ==============================================
# TEST POSTGRES CANCELLATION PERSISTS AND REPLAY IS REJECTED
# ==============================================


@pytest.mark.asyncio
async def test_postgres_cancellation_persists_and_replay_is_rejected(
    owner_client, order_graph
):
    g = order_graph
    for expected in [200, 422]:
        response = await owner_client.post(f"/api/v1/orders/{g.order_a}/cancel")
        assert response.status_code == expected, response.text
    assert (
        await scalar_from_new_session(
            g, select(Order.status).where(Order.id == g.order_a)
        )
        == "cancelled"
    )
    assert (
        await scalar_from_new_session(
            g, select(func.count()).select_from(OrderStatusHistory)
        )
        == 1
    )


# ==============================================
# TEST POSTGRES FULFILLMENT USES ONLY LEGAL TRANSITIONS
# ==============================================


@pytest.mark.asyncio
async def test_postgres_fulfillment_uses_only_legal_transitions(
    owner_client, order_graph
):
    g = order_graph
    premature = await owner_client.post(f"/api/v1/orders/{g.order_a}/complete")
    assert premature.status_code == 422
    for state in ["confirmed", "preparing", "ready", "delivering", "delivered"]:
        response = await owner_client.patch(
            f"/api/v1/orders/{g.order_a}/status", json={"status": state}
        )
        assert response.status_code == 200, response.text
    response = await owner_client.post(f"/api/v1/orders/{g.order_a}/complete")
    assert response.status_code == 200, response.text
    assert (
        await scalar_from_new_session(
            g, select(Order.status).where(Order.id == g.order_a)
        )
        == "completed"
    )
    assert (
        await scalar_from_new_session(
            g, select(func.count()).select_from(OrderStatusHistory)
        )
        == 6
    )


# ==============================================
# TEST POSTGRES PERMANENT DELETION COMMITS CHILDREN ATOMICALLY
# ==============================================


@pytest.mark.asyncio
async def test_postgres_permanent_deletion_commits_children_atomically(
    owner_client, order_graph
):
    g = order_graph
    response = await owner_client.delete(
        f"/api/v1/orders/{g.order_a}", params={"permanent": "true"}
    )
    assert response.status_code == 204, response.text
    assert (
        await scalar_from_new_session(g, select(func.count()).select_from(Order)) == 1
    )
    assert (
        await scalar_from_new_session(g, select(func.count()).select_from(OrderItem))
        == 0
    )
    assert (
        await scalar_from_new_session(g, select(func.count()).select_from(OrderPayment))
        == 1
    )


# ==============================================
# TEST POSTGRES CANCEL AND LEDGER REFUND ARE ATOMIC
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("fail_refund", [False, True])
async def test_postgres_cancel_and_ledger_refund_are_atomic(
    order_graph, monkeypatch, fail_refund
):
    from sqlalchemy import update
    from app.services.business.orders.cancel import cancel_order_with_refund
    from app.services.business.order_payments_service import OrderPaymentsService

    g = order_graph
    async with g.sessions() as writer:
        await writer.execute(
            update(OrderPayment)
            .where(OrderPayment.id == g.payment_a)
            .values(payment_status="paid")
        )
        await writer.commit()
    if fail_refund:
        original = OrderPaymentsService.refund_payment

        # ==============================================
        # FAIL AFTER REFUND
        # ==============================================

        async def fail_after_refund(self, **kwargs):
            await original(self, **kwargs)
            raise RuntimeError("injected refund failure")

        monkeypatch.setattr(OrderPaymentsService, "refund_payment", fail_after_refund)
    async with g.sessions() as writer:
        if fail_refund:
            with pytest.raises(RuntimeError):
                await cancel_order_with_refund(order_id=g.order_a, session=writer)
        else:
            await cancel_order_with_refund(order_id=g.order_a, session=writer)
    expected_order = "pending" if fail_refund else "cancelled"
    expected_payment = "paid" if fail_refund else "refunded"
    assert (
        await scalar_from_new_session(
            g, select(Order.status).where(Order.id == g.order_a)
        )
        == expected_order
    )
    assert (
        await scalar_from_new_session(
            g, select(OrderPayment.payment_status).where(OrderPayment.id == g.payment_a)
        )
        == expected_payment
    )
    assert await scalar_from_new_session(
        g, select(func.count()).select_from(OrderStatusHistory)
    ) == (0 if fail_refund else 1)
