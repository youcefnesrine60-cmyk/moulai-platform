# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""PostgreSQL regressions for billing callbacks and customer order payments."""

import asyncio
from datetime import (
    datetime,
    timedelta,
)
from types import SimpleNamespace

import pytest
from sqlalchemy import (
    func,
    insert,
    select,
    update,
)
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)
from app.models.order import Order
from app.models.order_item import OrderPayment
from app.models.owner import Owner
from app.models.payment import Payment
from app.models.restaurant import Restaurant
from app.models.restaurant_payment_setting import RestaurantPaymentSetting
from app.models.subscription import (
    Feature,
    Subscription,
    SubscriptionFeature,
    SubscriptionFeatureRequest,
    SubscriptionPlan,
)
from app.models.user import User
from app.repositories.subscription_features_repo import SubscriptionFeatureRepository
from app.services.business.order_payments_service import OrderPaymentsService
from app.services.business.payment_service import PaymentService


@pytest.fixture
async def payment_graph(db_session, sample_restaurant_data):
    async def put(model, **values):
        return (
            await db_session.execute(
                insert(model.__table__).values(**values).returning(model.id)
            )
        ).scalar_one()

    owner = await put(Owner, chat_id=81001, full_name="Billing owner")
    restaurant = await put(Restaurant, **dict(sample_restaurant_data, owner_id=owner))
    plan = await put(SubscriptionPlan, code="billing-test", name="Billing plan")
    subscription = await put(
        Subscription,
        owner_id=owner,
        restaurant_id=restaurant,
        plan_id=plan,
        billing_cycle="monthly",
        amount=50,
        status="pending",
    )
    feature = await put(Feature, code="billing-extra", name="Extra")
    await put(
        SubscriptionFeatureRequest, subscription_id=subscription, feature_id=feature
    )
    payment = await put(
        Payment,
        owner_id=owner,
        restaurant_id=restaurant,
        subscription_id=subscription,
        payment_method="card",
        amount=50,
        status="pending",
        external_reference="gateway-1",
    )
    user = await put(User, chat_id=82001, consent=True)
    other_user = await put(User, chat_id=82002, consent=True)
    order = await put(
        Order,
        user_id=user,
        restaurant_id=restaurant,
        order_number="PAY-1",
        order_type="takeaway",
        status="pending",
        total_amount=25,
    )
    await db_session.commit()
    return SimpleNamespace(
        owner=owner,
        restaurant=restaurant,
        plan=plan,
        subscription=subscription,
        payment=payment,
        feature=feature,
        order=order,
        other_user=other_user,
        sessions=async_sessionmaker(
            db_session.bind, expire_on_commit=False, autoflush=False
        ),
    )


async def snapshot(graph):
    async with graph.sessions() as reader:
        payment = (
            await reader.execute(
                select(
                    Payment.status,
                    Payment.paid_at,
                ).where(Payment.id == graph.payment)
            )
        ).one()
        subscription = (
            await reader.execute(
                select(
                    Subscription.status,
                    Subscription.starts_at,
                    Subscription.expires_at,
                ).where(Subscription.id == graph.subscription)
            )
        ).one()
        features = (
            await reader.execute(
                select(func.count())
                .select_from(SubscriptionFeature)
                .where(SubscriptionFeature.subscription_id == graph.subscription)
            )
        ).scalar_one()
        requests = (
            await reader.execute(
                select(func.count())
                .select_from(SubscriptionFeatureRequest)
                .where(SubscriptionFeatureRequest.subscription_id == graph.subscription)
            )
        ).scalar_one()
    return payment, subscription, features, requests


@pytest.mark.asyncio
@pytest.mark.parametrize("cycle,days", [("monthly", 30), ("yearly", 365)])
async def test_billing_success_commits_and_duplicate_does_not_extend(
    payment_graph, cycle, days
):
    g = payment_graph
    async with g.sessions() as session:
        await session.execute(
            update(Subscription)
            .where(Subscription.id == g.subscription)
            .values(billing_cycle=cycle)
        )
        await session.commit()
        await PaymentService(session=session).confirm_external_payment(
            external_reference="gateway-1"
        )
    first = await snapshot(g)
    assert first[0].status == "paid"
    assert first[0].paid_at == first[1].starts_at
    assert first[1].status == "active"
    assert first[1].expires_at - first[1].starts_at == timedelta(days=days)
    assert first[2:] == (1, 0)
    async with g.sessions() as session:
        await PaymentService(session=session).confirm_external_payment(
            external_reference="gateway-1"
        )
        await PaymentService(session=session).fail_external_payment(
            external_reference="gateway-1"
        )
    assert await snapshot(g) == first


@pytest.mark.asyncio
async def test_feature_failure_rolls_back_payment_and_activation(
    payment_graph, monkeypatch
):
    g = payment_graph
    original = SubscriptionFeatureRepository.create_subscription_feature

    async def fail_after_feature(self, **kwargs):
        await original(self, **kwargs)
        raise RuntimeError("feature transfer failed")

    monkeypatch.setattr(
        SubscriptionFeatureRepository, "create_subscription_feature", fail_after_feature
    )
    async with g.sessions() as session:
        with pytest.raises(RuntimeError, match="feature transfer failed"):
            await PaymentService(session=session).confirm_external_payment(
                external_reference="gateway-1"
            )
        assert "defer_repository_commit" not in session.info
    result = await snapshot(g)
    assert result[0] == ("pending", None)
    assert result[1] == ("pending", None, None)
    assert result[2:] == (0, 1)


@pytest.mark.asyncio
async def test_billing_preserves_caller_transaction_and_autobegin(payment_graph):
    g = payment_graph
    async with g.sessions() as session:
        await session.begin()
        session.info["defer_repository_commit"] = "caller"
        await PaymentService(session=session).confirm_external_payment(
            external_reference="gateway-1"
        )
        assert session.in_transaction()
        assert session.info["defer_repository_commit"] == "caller"
        assert (await snapshot(g))[0].status == "pending"
        await session.rollback()
    assert (await snapshot(g))[2:] == (0, 1)
    async with g.sessions() as session:
        await session.execute(select(Payment.id).where(Payment.id == g.payment))
        await PaymentService(session=session).confirm_external_payment(
            external_reference="gateway-1"
        )
    assert (await snapshot(g))[0].status == "paid"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["missing", "cycle", "scope", "cancelled"])
async def test_billing_rejects_invalid_event_without_writes(payment_graph, case):
    g = payment_graph
    async with g.sessions() as session:
        if case == "cycle":
            await session.execute(
                update(Subscription)
                .where(Subscription.id == g.subscription)
                .values(billing_cycle="quarterly")
            )
        elif case == "scope":
            owner = (
                await session.execute(
                    insert(Owner.__table__)
                    .values(chat_id=81003, full_name="Other")
                    .returning(Owner.id)
                )
            ).scalar_one()
            await session.execute(
                update(Payment).where(Payment.id == g.payment).values(owner_id=owner)
            )
        elif case == "cancelled":
            await session.execute(
                update(Subscription)
                .where(Subscription.id == g.subscription)
                .values(status="cancelled")
            )
        await session.commit()
        with pytest.raises(ValueError):
            await PaymentService(session=session).confirm_external_payment(
                external_reference="missing" if case == "missing" else "gateway-1",
            )
    result = await snapshot(g)
    assert result[0] == ("pending", None)
    assert result[2:] == (0, 1)


@pytest.mark.asyncio
async def test_failure_is_idempotent_and_does_not_activate_subscription(payment_graph):
    g = payment_graph
    async with g.sessions() as session:
        service = PaymentService(session=session)
        await service.fail_external_payment(external_reference="gateway-1")
        await service.fail_external_payment(external_reference="gateway-1")
        with pytest.raises(ValidationError):
            await service.confirm_external_payment(external_reference="gateway-1")
    result = await snapshot(g)
    assert result[0] == ("failed", None)
    assert result[1] == ("pending", None, None)
    assert result[2:] == (0, 1)


@pytest.mark.asyncio
async def test_concurrent_duplicate_success_creates_features_once(payment_graph):
    g = payment_graph

    async def confirm():
        async with g.sessions() as session:
            await PaymentService(session=session).confirm_external_payment(
                external_reference="gateway-1"
            )

    await asyncio.wait_for(asyncio.gather(confirm(), confirm()), timeout=60)
    result = await snapshot(g)
    assert result[0].status == "paid"
    assert result[2:] == (1, 0)


@pytest.mark.asyncio
async def test_customer_payment_uses_order_table_amount_and_is_idempotent(
    payment_graph,
):
    g = payment_graph
    async with g.sessions() as session:
        service = OrderPaymentsService(session=session)
        first = await service.submit_customer_payment(
            chat_id=82001, order_id=g.order, payment_method="cash"
        )
        second = await service.submit_customer_payment(
            chat_id=82001, order_id=g.order, payment_method="cash"
        )
    assert first.id == second.id
    assert first.amount == 25
    assert first.payment_status == "pending"
    assert first.paid_at is None
    async with g.sessions() as reader:
        assert (
            await reader.execute(
                select(func.count())
                .select_from(OrderPayment)
                .where(OrderPayment.order_id == g.order)
            )
        ).scalar_one() == 1
        assert (
            await reader.execute(select(func.count()).select_from(Payment))
        ).scalar_one() == 1
        assert (
            await reader.execute(select(Order.status).where(Order.id == g.order))
        ).scalar_one() == "pending"


@pytest.mark.asyncio
async def test_customer_payment_denies_other_customer(payment_graph):
    g = payment_graph
    async with g.sessions() as session:
        with pytest.raises(NotFoundError):
            await OrderPaymentsService(session=session).submit_customer_payment(
                chat_id=82002, order_id=g.order, payment_method="cash"
            )
        assert (
            await session.execute(select(func.count()).select_from(OrderPayment))
        ).scalar_one() == 0


@pytest.mark.asyncio
async def test_customer_payment_quote_is_owned_and_uses_persisted_amount(payment_graph):
    g = payment_graph
    async with g.sessions() as session:
        service = OrderPaymentsService(session=session)
        amount, methods = await service.get_customer_payment_options(
            chat_id=82001, order_id=g.order
        )
        assert amount == 25
        assert methods == {"cash", "card"}
        with pytest.raises(NotFoundError):
            await service.get_customer_payment_options(chat_id=82002, order_id=g.order)


@pytest.mark.asyncio
async def test_explicitly_disabled_order_methods_are_not_defaulted(payment_graph):
    g = payment_graph
    async with g.sessions() as session:
        await session.execute(
            insert(RestaurantPaymentSetting.__table__).values(
                restaurant_id=g.restaurant,
                allow_cash=False,
                allow_card=False,
                allow_ccp=False,
                allow_baridimob=False,
                allow_stripe=False,
                allow_paypal=False,
            )
        )
        await session.commit()
        service = OrderPaymentsService(session=session)
        assert (
            await service.get_customer_payment_options(chat_id=82001, order_id=g.order)
        )[1] == set()
        with pytest.raises(ValidationError):
            await service.submit_customer_payment(
                chat_id=82001, order_id=g.order, payment_method="cash"
            )


@pytest.mark.asyncio
async def test_customer_confirmation_failure_removes_new_payment(
    payment_graph, monkeypatch
):
    original = OrderPaymentsService.create_payment

    async def fail_create(self, **kwargs):
        await original(self, **kwargs)
        raise RuntimeError("confirmation failed")

    monkeypatch.setattr(OrderPaymentsService, "create_payment", fail_create)
    async with payment_graph.sessions() as session:
        with pytest.raises(RuntimeError, match="confirmation failed"):
            await OrderPaymentsService(session=session).submit_customer_payment(
                chat_id=82001, order_id=payment_graph.order, payment_method="cash"
            )
    async with payment_graph.sessions() as reader:
        assert (
            await reader.execute(select(func.count()).select_from(OrderPayment))
        ).scalar_one() == 0


@pytest.mark.asyncio
async def test_active_subscription_keeps_its_original_dates(payment_graph):
    g = payment_graph
    starts = datetime(2026, 10, 1)  # noqa: DTZ001 - Existing DB columns store naive UTC.
    expires = starts + timedelta(days=30)
    async with g.sessions() as session:
        await session.execute(
            update(Subscription)
            .where(Subscription.id == g.subscription)
            .values(status="active", starts_at=starts, expires_at=expires)
        )
        await session.commit()
        await PaymentService(session=session).confirm_external_payment(
            external_reference="gateway-1"
        )
    result = await snapshot(g)
    assert result[1] == ("active", starts, expires)
    assert result[2:] == (1, 0)
