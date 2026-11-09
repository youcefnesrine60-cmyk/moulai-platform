# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# CASH COLLECTION SAFETY REGRESSIONS
# Check authority, matching funds, atomic activation and duplicate handling for cash
# requests.
# ==============================================

"""Cash collection uses synthetic identities and disposable local PostgreSQL only."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

import asyncio
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from types import SimpleNamespace
from typing import Never

import pytest
from sqlalchemy import (
    Row,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.core.exceptions import (
    ConflictError,
    UnauthorizedError,
    ValidationError,
)
from app.models.admin import Admin
from app.models.cash_collection import (
    CashCollection,
    CashCollectionAttempt,
)
from app.models.payment import Payment
from app.models.rbac import (
    Permission,
    Role,
    role_permissions,
)
from app.models.subscription import (
    Subscription,
    SubscriptionFeature,
)
from app.schemas.manual_payment import ManualSubscriptionCheckout
from app.schemas.payment import PaymentResponse
from app.services.business.cash_collection_service import CashCollectionService
from app.services.business.manual_payment_service import ManualPaymentService
from app.services.business.payment_service import PaymentService

from app.services.business.subscription_checkout_service import SubscriptionCheckoutService  # isort: skip  # fmt: skip
from app.services.business.subscription_service import SubscriptionService
from test_support.subscription_fixtures import (
    closed_trial,
    put,
    seed_graph,
)

# ==============================================
# CASH
# Prepare a synthetic pending cash request, authorized collector and matching receipt
# facts.
# ==============================================


@pytest.fixture
async def cash(db_session: AsyncSession) -> SimpleNamespace:
    """Prepare a synthetic pending cash request, authorized collector and matching receipt facts."""

    g = await seed_graph(db_session)
    await closed_trial(g)
    g.data = ManualSubscriptionCheckout(
        restaurant_id=g.restaurant, plan_id=g.plans["basic"], payment_method="cash"
    )
    g.invoice = await SubscriptionCheckoutService(session=g.s).create(
        owner_id=g.owner, data=g.data
    )
    role = await put(g.s, Role, code="cash", name="Synthetic collector", is_active=True)
    permission = await put(g.s, Permission, code="payments.cash.collect", name="Cash")
    await g.s.execute(
        insert(role_permissions).values(role_id=role, permission_id=permission)
    )
    g.admin = await put(g.s, Admin, role_id=role, chat_id=9908001)
    g.role = role
    await g.s.commit()
    g.sessions = async_sessionmaker(g.s.bind, expire_on_commit=False)
    g.service = CashCollectionService(session_factory=g.sessions)
    g.facts = {
        "received_amount": Decimal(str(g.invoice.amount)),
        "currency": "DZD",
        "collected_at": datetime.now(timezone.utc) - timedelta(seconds=1),
        "receipt_reference": "SYNTHETIC-CASH-001",
    }
    return g


# ==============================================
# STATE
# Read the synthetic invoice and linked subscription settlement states together.
# ==============================================


async def state(g: SimpleNamespace) -> Row[tuple[str, str]]:
    """Read the synthetic invoice and linked subscription settlement states together."""

    async with g.sessions() as s:
        return (
            await s.execute(
                select(Payment.status, Subscription.status)
                .join(Subscription, Subscription.id == Payment.subscription_id)
                .where(Payment.id == g.invoice.id)
            )
        ).one()


# ==============================================
# TEST CASH PENDING QUOTE AND RETRY NEVER ACTIVATE
# Verify cash pending quote and retry never activate.
# ==============================================


@pytest.mark.asyncio
async def test_cash_pending_quote_and_retry_never_activate(
    cash: SimpleNamespace,
) -> None:
    """Verify cash pending quote and retry never activate."""

    g = cash
    assert Decimal(str(g.invoice.amount)) == Decimal("3060.00")
    assert await state(g) == ("pending", "pending")
    assert (
        await SubscriptionCheckoutService(session=g.s).create(
            owner_id=g.owner, data=g.data
        )
    ).id == g.invoice.id
    count = (
        await g.s.execute(
            select(func.count())
            .select_from(SubscriptionFeature)
            .where(SubscriptionFeature.subscription_id == g.invoice.subscription_id)
        )
    ).scalar_one()
    assert count == 0
    assert isinstance(g.invoice.amount, Decimal)
    exact = g.invoice.model_copy(update={"amount": Decimal("9999999999999999.99")})
    assert exact.model_dump(mode="json")["amount"] == "9999999999999999.99"


# ==============================================
# TEST CASH VALID RECEIPT ACTIVATES ATOMICALLY AND IS IDEMPOTENT
# Verify cash valid receipt activates atomically and is idempotent.
# ==============================================


@pytest.mark.asyncio
async def test_cash_valid_receipt_activates_atomically_and_is_idempotent(
    cash: SimpleNamespace,
) -> None:
    """Verify cash valid receipt activates atomically and is idempotent."""

    g = cash
    args = {"payment_id": g.invoice.id, "admin_id": g.admin, "data": g.facts}
    first = await g.service.confirm(**args)
    assert first["result"] == "confirmed"
    assert await state(g) == ("paid", "active")
    again = await g.service.confirm(**args)
    assert again == first | {"result": "idempotent"}
    async with g.sessions() as s:
        receipt = (await s.execute(select(CashCollection))).scalar_one()
        assert receipt.expected_amount == receipt.received_amount == Decimal(3060)
        assert receipt.admin_id == g.admin
        assert receipt.subscription_id == g.invoice.subscription_id
        assert receipt.collected_at == g.facts["collected_at"].replace(tzinfo=None)
        assert receipt.currency == "DZD"
        assert receipt.receipt_reference == "SYNTHETICCASH001"
        grants = (
            await s.execute(
                select(func.count())
                .select_from(SubscriptionFeature)
                .where(SubscriptionFeature.subscription_id == g.invoice.subscription_id)
            )
        ).scalar_one()
        assert grants == 6
        assert list(
            (
                await s.execute(
                    select(CashCollectionAttempt.result).order_by(
                        CashCollectionAttempt.id
                    )
                )
            ).scalars()
        ) == ["requested", "confirmed", "requested", "idempotent"]


# ==============================================
# TEST CASH INVALID FACTS REJECTED AND AUDITED
# Verify cash invalid facts rejected and audited.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        {"received_amount": Decimal("3059.99")},
        {"currency": "USD"},
        {"collected_at": datetime(2099, 1, 1, tzinfo=timezone.utc)},
        {"received_amount": Decimal("NaN")},
        {"receipt_reference": "***"},
    ],
)
async def test_cash_invalid_facts_rejected_and_audited(
    cash: SimpleNamespace, change: dict[str, object]
) -> None:
    """Verify cash invalid facts rejected and audited."""

    g = cash
    with pytest.raises((ValidationError, ValueError)):
        await g.service.confirm(
            payment_id=g.invoice.id, admin_id=g.admin, data=g.facts | change
        )
    assert await state(g) == ("pending", "pending")
    async with g.sessions() as s:
        assert (
            await s.execute(select(func.count()).select_from(CashCollection))
        ).scalar_one() == 0
        assert (
            await s.execute(select(func.count()).select_from(CashCollectionAttempt))
        ).scalar_one() == 2


# ==============================================
# TEST CASH REQUIRES EXPLICIT DISTINCT PERMISSION
# Verify cash requires explicit distinct permission.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("permission", ["payments.review", "*", None])
async def test_cash_requires_explicit_distinct_permission(
    cash: SimpleNamespace, permission: str | None
) -> None:
    """Verify cash requires explicit distinct permission."""

    g = cash
    from sqlalchemy import delete

    await g.s.execute(
        delete(role_permissions).where(role_permissions.c.role_id == g.role)
    )
    if permission:
        pid = await put(g.s, Permission, code=permission, name="Synthetic other grant")
        await g.s.execute(
            insert(role_permissions).values(role_id=g.role, permission_id=pid)
        )
    await g.s.commit()
    with pytest.raises(UnauthorizedError):
        await g.service.confirm(payment_id=g.invoice.id, admin_id=g.admin, data=g.facts)
    assert await state(g) == ("pending", "pending")


# ==============================================
# TEST CASH UPLOAD AND GENERIC SETTLEMENT CANNOT CONFIRM
# Verify cash upload and generic settlement cannot confirm.
# ==============================================


@pytest.mark.asyncio
async def test_cash_upload_and_generic_settlement_cannot_confirm(
    cash: SimpleNamespace,
) -> None:
    """Verify cash upload and generic settlement cannot confirm."""

    g = cash
    with pytest.raises(ValidationError):
        await ManualPaymentService(session=g.s).submit_receipt(
            payment_id=g.invoice.id,
            owner_id=g.owner,
            transaction_reference="OWNER-ASSERTION",
            content=b"\x89PNG\r\n\x1a\nsynthetic",
            media_type="image/png",
        )
    with pytest.raises(ValidationError, match="Verified physical cash receipt"):
        await PaymentService(session=g.s).confirm_payment(payment_id=g.invoice.id)
    assert await state(g) == ("pending", "pending")
    from app.schemas.payment import PaymentStatusUpdate

    with pytest.raises(ValidationError, match="physical collection workflow"):
        await PaymentService(session=g.s).update_payment_status(
            payment_id=g.invoice.id, status_data=PaymentStatusUpdate(status="paid")
        )


# ==============================================
# TEST CONCURRENT CASH CONFIRMATIONS DO NOT DUPLICATE
# Verify concurrent cash confirmations do not duplicate.
# ==============================================


@pytest.mark.asyncio
async def test_concurrent_cash_confirmations_do_not_duplicate(
    cash: SimpleNamespace,
) -> None:
    """Verify concurrent cash confirmations do not duplicate."""

    g = cash
    args = {"payment_id": g.invoice.id, "admin_id": g.admin, "data": g.facts}
    results = await asyncio.gather(g.service.confirm(**args), g.service.confirm(**args))
    assert sorted(r["result"] for r in results) == ["confirmed", "idempotent"]
    async with g.sessions() as s:
        assert (
            await s.execute(select(func.count()).select_from(CashCollection))
        ).scalar_one() == 1
        assert (
            await s.execute(select(func.count()).select_from(CashCollectionAttempt))
        ).scalar_one() == 4
    assert await state(g) == ("paid", "active")


# ==============================================
# TEST CONCURRENT CASH REQUESTS REUSE ONE INVOICE
# Verify concurrent cash requests reuse one invoice.
# ==============================================


@pytest.mark.asyncio
async def test_concurrent_cash_requests_reuse_one_invoice(
    cash: SimpleNamespace,
) -> None:
    """Verify concurrent cash requests reuse one invoice."""

    g = cash

    # ==============================================
    # RETRY
    # Repeat the identical synthetic checkout in a separate session to verify invoice
    # reuse.
    # ==============================================

    async def retry() -> PaymentResponse:
        """Repeat the identical synthetic checkout in a separate session to verify invoice reuse."""

        async with g.sessions() as s:
            return await SubscriptionCheckoutService(session=s).create(
                owner_id=g.owner, data=g.data
            )

    results = await asyncio.gather(retry(), retry())
    assert {r.id for r in results} == {g.invoice.id}
    assert await state(g) == ("pending", "pending")


# ==============================================
# TEST DIFFERENT SECOND CONFIRMATION REFUSED WITHOUT CHANGING RECEIPT
# Verify different second confirmation refused without changing receipt.
# ==============================================


@pytest.mark.asyncio
async def test_different_second_confirmation_refused_without_changing_receipt(
    cash: SimpleNamespace,
) -> None:
    """Verify different second confirmation refused without changing receipt."""

    g = cash
    await g.service.confirm(payment_id=g.invoice.id, admin_id=g.admin, data=g.facts)
    with pytest.raises(ConflictError):
        await g.service.confirm(
            payment_id=g.invoice.id,
            admin_id=g.admin,
            data=g.facts | {"receipt_reference": "SYNTHETIC-OTHER"},
        )
    assert await state(g) == ("paid", "active")


# ==============================================
# TEST CASH INACTIVE COLLECTOR REFUSED
# Verify cash inactive collector refused.
# ==============================================


@pytest.mark.asyncio
async def test_cash_inactive_collector_refused(cash: SimpleNamespace) -> None:
    """Verify cash inactive collector refused."""

    g = cash
    await g.s.execute(update(Admin).where(Admin.id == g.admin).values(is_active=False))
    await g.s.commit()
    with pytest.raises(UnauthorizedError):
        await g.service.confirm(payment_id=g.invoice.id, admin_id=g.admin, data=g.facts)
    assert await state(g) == ("pending", "pending")


# ==============================================
# TEST CASH ACTIVATION FAILURE ROLLS BACK RECEIPT AND PAYMENT
# Verify cash activation failure rolls back receipt and payment.
# ==============================================


@pytest.mark.asyncio
async def test_cash_activation_failure_rolls_back_receipt_and_payment(
    cash: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify cash activation failure rolls back receipt and payment."""

    # ==============================================
    # FAIL
    # Inject a controlled failure to verify transaction rollback.
    # ==============================================

    async def fail(*args: object, **kwargs: object) -> Never:
        """Inject a controlled failure to verify transaction rollback."""

        raise ValueError("synthetic_activation_failure")

    monkeypatch.setattr(SubscriptionService, "activate_for_verified_payment", fail)
    g = cash
    with pytest.raises(ValueError, match="synthetic_activation_failure"):
        await g.service.confirm(payment_id=g.invoice.id, admin_id=g.admin, data=g.facts)
    assert await state(g) == ("pending", "pending")
    async with g.sessions() as s:
        assert (
            await s.execute(select(func.count()).select_from(CashCollection))
        ).scalar_one() == 0
        assert (
            await s.execute(select(func.count()).select_from(CashCollectionAttempt))
        ).scalar_one() == 2


# ==============================================
# TEST CASH EVIDENCE AND ATTEMPTS ARE IMMUTABLE
# Verify cash evidence and attempts are immutable.
# ==============================================


@pytest.mark.asyncio
async def test_cash_evidence_and_attempts_are_immutable(cash: SimpleNamespace) -> None:
    """Verify cash evidence and attempts are immutable."""

    from sqlalchemy.exc import DBAPIError

    g = cash
    await g.service.confirm(payment_id=g.invoice.id, admin_id=g.admin, data=g.facts)
    async with g.sessions() as s:
        for statement in [
            update(CashCollection).values(receipt_reference="CHANGED"),
            update(CashCollectionAttempt).values(result="changed"),
            update(Payment).where(Payment.id == g.invoice.id).values(amount=1),
        ]:
            with pytest.raises(DBAPIError):
                async with s.begin_nested():
                    await s.execute(statement)
            await s.rollback()
    assert await state(g) == ("paid", "active")


# ==============================================
# TEST UNKNOWN CASH PAYMENT ATTEMPT IS RETAINED
# Verify unknown cash payment attempt is retained.
# ==============================================


@pytest.mark.asyncio
async def test_unknown_cash_payment_attempt_is_retained(cash: SimpleNamespace) -> None:
    """Verify unknown cash payment attempt is retained."""

    from app.core.exceptions import NotFoundError

    g = cash
    with pytest.raises(NotFoundError):
        await g.service.confirm(payment_id=999999, admin_id=g.admin, data=g.facts)
    async with g.sessions() as s:
        events = list(
            (
                await s.execute(
                    select(CashCollectionAttempt.result)
                    .where(CashCollectionAttempt.payment_id == 999999)
                    .order_by(CashCollectionAttempt.id)
                )
            ).scalars()
        )
        assert events == ["requested", "NotFoundError"]


# ==============================================
# TEST CASH CANNOT REUSE ELECTRONIC QUOTE AND CANCELLED QUOTE CAN BE REPLACED
# Verify cash cannot reuse electronic quote and cancelled quote can be replaced.
# ==============================================


@pytest.mark.asyncio
async def test_cash_cannot_reuse_electronic_quote_and_cancelled_quote_can_be_replaced(
    cash: SimpleNamespace,
) -> None:
    """Verify cash cannot reuse electronic quote and cancelled quote can be replaced."""

    from app.schemas.payment import PaymentCreate

    g = cash
    # Method mismatch must be rejected before issuing another invoice.
    with pytest.raises(ValidationError, match="retained quote"):
        await PaymentService(session=g.s).create_payment(
            payment_data=PaymentCreate(
                owner_id=g.owner,
                restaurant_id=g.restaurant,
                subscription_id=g.invoice.subscription_id,
                payment_method="ccp",
                amount=Decimal(str(g.invoice.amount)),
            )
        )
    await g.s.execute(
        update(Payment).where(Payment.id == g.invoice.id).values(status="cancelled")
    )
    await g.s.execute(
        update(Subscription)
        .where(Subscription.id == g.invoice.subscription_id)
        .values(status="cancelled")
    )
    await g.s.commit()
    # A cancelled pending subscription has no purchased service period. It is
    # not an active historical reference and cannot hide the preceding trial.
    replacement = await SubscriptionCheckoutService(session=g.s).create(
        owner_id=g.owner, data=g.data
    )
    assert replacement.id != g.invoice.id
    assert replacement.amount == g.invoice.amount
