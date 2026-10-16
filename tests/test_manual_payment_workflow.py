# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Real PostgreSQL proofs for private evidence and administrative settlement."""

import asyncio
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import (
    Any,
    Never,
    Protocol,
    TypeAlias,
)

import pytest
from httpx import AsyncClient
from sqlalchemy import (
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.api import auth
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.main import app
from app.models.admin import Admin
from app.models.base import BaseModel
from app.models.manual_payment import (
    ManualPaymentAudit,
    ManualPaymentReceipt,
)
from app.models.owner import Owner
from app.models.payment import Payment
from app.models.rbac import (
    Permission,
    Role,
    role_permissions,
)
from app.models.restaurant import Restaurant
from app.models.subscription import (
    Feature,
    Subscription,
    SubscriptionFeature,
    SubscriptionFeatureRequest,
    SubscriptionPlan,
)
from app.repositories.manual_payment_repo import ManualPaymentRepository
from app.repositories.subscription_features_repo import SubscriptionFeatureRepository
from app.schemas.manual_payment import (
    ManualPaymentReview,
    ManualSubscriptionCheckout,
)
from app.services.business.manual_payment_service import ManualPaymentService
from app.services.business.subscription_checkout_service import SubscriptionCheckoutService  # fmt: skip

CONTENT = b"\x89PNG\r\n\x1a\nprivate-test-receipt"


# ==============================================
# FIXTURE AND PERSISTED STATE TYPES
# ==============================================


class ManualGraph(Protocol):
    """Identify the two isolated tenants and the sessions used by workflow proofs."""

    owner: int
    other_owner: int
    restaurant: int
    plan: int
    payment: int
    other_payment: int
    subscription: int
    reviewer: int
    denied: int
    sessions: async_sessionmaker[AsyncSession]


StateSnapshot: TypeAlias = tuple[
    Row[tuple[str, datetime | None]],
    Row[tuple[str, datetime | None, datetime | None]],
    int,
    int,
    str,
]


@pytest.fixture
async def manual_graph(
    db_session: AsyncSession, sample_restaurant_data: dict[str, Any]
) -> ManualGraph:
    """Persist separate tenants, pending invoices, and live administrative roles."""

    async def put(model: type[BaseModel], **values: Any) -> int:
        """Insert a fixture through SQLAlchemy and return its generated primary key."""
        return (
            await db_session.execute(
                insert(model.__table__).values(**values).returning(model.id)
            )
        ).scalar_one()

    reviewer_role = await put(Role, code="finance", name="Finance", is_active=True)
    denied_role = await put(Role, code="support", name="Support", is_active=True)
    permission = await put(Permission, code="payments.review", name="Review payments")
    await db_session.execute(
        insert(role_permissions).values(role_id=reviewer_role, permission_id=permission)
    )
    reviewer = await put(
        Admin, chat_id=83001, role_id=reviewer_role, auth_subject="finance-subject"
    )
    denied = await put(Admin, chat_id=83002, role_id=denied_role)
    owner = await put(Owner, chat_id=84001, auth_subject="tenant-a")
    other_owner = await put(Owner, chat_id=84002, auth_subject="tenant-b")
    restaurant = await put(Restaurant, **dict(sample_restaurant_data, owner_id=owner))
    other_restaurant = await put(
        Restaurant, **dict(sample_restaurant_data, owner_id=other_owner)
    )
    plan = await put(SubscriptionPlan, code="manual-test", name="Manual", base_price=50)
    subscription = await put(
        Subscription,
        owner_id=owner,
        restaurant_id=restaurant,
        plan_id=plan,
        billing_cycle="monthly",
        amount=50,
        status="pending",
    )
    other_subscription = await put(
        Subscription,
        owner_id=other_owner,
        restaurant_id=other_restaurant,
        plan_id=plan,
        billing_cycle="monthly",
        amount=50,
        status="pending",
    )
    feature = await put(Feature, code="manual-extra", name="Extra")
    await put(
        SubscriptionFeatureRequest, subscription_id=subscription, feature_id=feature
    )
    payment = await put(
        Payment,
        owner_id=owner,
        restaurant_id=restaurant,
        subscription_id=subscription,
        payment_method="ccp",
        payment_provider="manual_transfer",
        amount=50,
        status="pending",
    )
    other_payment = await put(
        Payment,
        owner_id=other_owner,
        restaurant_id=other_restaurant,
        subscription_id=other_subscription,
        payment_method="baridimob",
        payment_provider="manual_transfer",
        amount=50,
        status="pending",
    )
    await db_session.commit()
    return SimpleNamespace(
        owner=owner,
        other_owner=other_owner,
        restaurant=restaurant,
        plan=plan,
        payment=payment,
        other_payment=other_payment,
        subscription=subscription,
        reviewer=reviewer,
        denied=denied,
        sessions=async_sessionmaker(
            db_session.bind, expire_on_commit=False, autoflush=False
        ),
    )


def approval(**changes: Any) -> ManualPaymentReview:
    """Build verified bank evidence with explicit overrides for validation cases."""
    return ManualPaymentReview(
        **(
            {
                "decision": "approve",
                "funds_received": True,
                "bank_transaction_reference": "CCP-12345",
                "received_amount": Decimal("50.00"),
                "received_currency": "DZD",
                "note": "Bank credit independently checked",
            }
            | changes
        )
    )


async def upload(g: ManualGraph) -> ManualPaymentReceipt:
    """Store private evidence using the owning tenant and an independent session."""
    async with g.sessions() as session:
        return await ManualPaymentService(session=session).submit_receipt(
            payment_id=g.payment,
            owner_id=g.owner,
            transaction_reference="CCP-12345",
            content=CONTENT,
            media_type="image/png",
        )


async def state(g: ManualGraph) -> StateSnapshot:
    """Read payment, subscription, feature, and audit state from persisted rows."""
    async with g.sessions() as session:
        return (
            (
                await session.execute(
                    select(Payment.status, Payment.paid_at).where(
                        Payment.id == g.payment
                    )
                )
            ).one(),
            (
                await session.execute(
                    select(
                        Subscription.status,
                        Subscription.starts_at,
                        Subscription.expires_at,
                    ).where(Subscription.id == g.subscription)
                )
            ).one(),
            (
                await session.execute(
                    select(func.count()).select_from(SubscriptionFeature)
                )
            ).scalar_one(),
            (
                await session.execute(
                    select(func.count()).select_from(ManualPaymentAudit)
                )
            ).scalar_one(),
            (
                await session.execute(
                    select(ManualPaymentReceipt.review_status).where(
                        ManualPaymentReceipt.payment_id == g.payment
                    )
                )
            ).scalar_one(),
        )


@pytest.mark.asyncio
async def test_upload_does_not_settle_and_exact_retry_creates_one_audit(
    manual_graph: ManualGraph,
) -> None:
    """Ensure upload does not settle and exact retry creates one audit."""
    g = manual_graph
    first = await upload(g)
    second = await upload(g)
    assert first.id == second.id
    snapshot = await state(g)
    assert snapshot[0] == ("pending", None)
    assert snapshot[1] == ("pending", None, None)
    assert snapshot[2:] == (0, 1, "pending")


@pytest.mark.asyncio
@pytest.mark.parametrize("duplicate", ["file", "reference"])
async def test_evidence_cannot_be_reused_across_tenants(
    manual_graph: ManualGraph, duplicate: str
) -> None:
    """Ensure evidence cannot be reused across tenants."""
    g = manual_graph
    await upload(g)
    async with g.sessions() as session:
        with pytest.raises(ConflictError):
            await ManualPaymentService(session=session).submit_receipt(
                payment_id=g.other_payment,
                owner_id=g.other_owner,
                transaction_reference="CCP / 12345"
                if duplicate == "reference"
                else "OTHER-123",
                content=CONTENT if duplicate == "file" else CONTENT + b"other",
                media_type="image/png",
            )
    assert (await state(g))[3] == 1


@pytest.mark.asyncio
async def test_foreign_owner_is_denied_before_read_or_write(
    manual_graph: ManualGraph,
) -> None:
    """Ensure foreign owner is denied before read or write."""
    g = manual_graph
    async with g.sessions() as session:
        service = ManualPaymentService(session=session)
        with pytest.raises(NotFoundError):
            await service.submit_receipt(
                payment_id=g.payment,
                owner_id=g.other_owner,
                transaction_reference="CCP-12345",
                content=CONTENT,
                media_type="image/png",
            )
        with pytest.raises(NotFoundError):
            await service.get_receipt(payment_id=g.payment, owner_id=g.other_owner)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [{"received_amount": "49.99"}, {"bank_transaction_reference": "WRONG123"}],
)
async def test_review_requires_matching_independent_funds(
    manual_graph: ManualGraph, changes: dict[str, Any]
) -> None:
    """Ensure review requires matching independent funds."""
    g = manual_graph
    await upload(g)
    async with g.sessions() as session:
        with pytest.raises(ValidationError):
            await ManualPaymentService(session=session).review(
                payment_id=g.payment, admin_id=g.reviewer, data=approval(**changes)
            )
    assert (await state(g))[2:] == (0, 1, "pending")


@pytest.mark.asyncio
@pytest.mark.parametrize("denial", ["permission", "inactive"])
async def test_review_checks_live_database_rbac(
    manual_graph: ManualGraph, denial: str
) -> None:
    """Ensure review checks live database rbac."""
    g = manual_graph
    await upload(g)
    async with g.sessions() as session:
        if denial == "inactive":
            await session.execute(
                update(Admin).where(Admin.id == g.reviewer).values(is_active=False)
            )
            await session.commit()
        with pytest.raises(UnauthorizedError):
            await ManualPaymentService(session=session).review(
                payment_id=g.payment,
                admin_id=g.denied if denial == "permission" else g.reviewer,
                data=approval(),
            )
    assert (await state(g))[2:] == (0, 1, "pending")


@pytest.mark.asyncio
async def test_concurrent_review_settles_once_and_preserves_subscription_dates(
    manual_graph: ManualGraph,
) -> None:
    """Ensure concurrent review settles once and preserves subscription dates."""
    g = manual_graph
    await upload(g)

    async def review() -> ManualPaymentReceipt:
        """Approve the same verified invoice from a separate database session."""
        async with g.sessions() as session:
            return await ManualPaymentService(session=session).review(
                payment_id=g.payment, admin_id=g.reviewer, data=approval()
            )

    receipts = await asyncio.wait_for(asyncio.gather(review(), review()), timeout=60)
    assert receipts[0].id == receipts[1].id
    snapshot = await state(g)
    assert snapshot[0].status == "paid"
    assert snapshot[1].status == "active"
    assert snapshot[2:] == (1, 2, "approved")
    await review()
    assert await state(g) == snapshot


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_point", ["feature", "audit"])
async def test_review_rolls_back_every_effect_when_final_write_fails(
    manual_graph: ManualGraph, monkeypatch: pytest.MonkeyPatch, failure_point: str
) -> None:
    """Ensure review rolls back every effect when final write fails."""
    g = manual_graph
    await upload(g)
    if failure_point == "feature":
        original = SubscriptionFeatureRepository.create_subscription_feature

        async def fail(self: SubscriptionFeatureRepository, **kwargs: Any) -> Never:
            """Inject a failure after the actual final write to prove complete rollback."""
            await original(self, **kwargs)
            raise RuntimeError("final write failed")

        monkeypatch.setattr(
            SubscriptionFeatureRepository, "create_subscription_feature", fail
        )
    else:
        original = ManualPaymentRepository.append_audit

        async def fail(self: ManualPaymentRepository, **kwargs: Any) -> Never:
            """Inject a failure after the actual final write to prove complete rollback."""
            await original(self, **kwargs)
            raise RuntimeError("final write failed")

        monkeypatch.setattr(ManualPaymentRepository, "append_audit", fail)
    async with g.sessions() as session:
        # Start AUTOBEGIN before entering the outer transaction, as API auth does.
        await session.execute(select(Payment.id).where(Payment.id == g.payment))
        with pytest.raises(RuntimeError, match="final write failed"):
            await ManualPaymentService(session=session).review(
                payment_id=g.payment, admin_id=g.reviewer, data=approval()
            )
        assert "defer_repository_commit" not in session.info
    snapshot = await state(g)
    assert snapshot[0] == ("pending", None)
    assert snapshot[1] == ("pending", None, None)
    assert snapshot[2:] == (0, 1, "pending")


@pytest.mark.asyncio
async def test_rejection_cannot_later_be_approved_and_does_not_activate(
    manual_graph: ManualGraph,
) -> None:
    """Ensure rejection cannot later be approved and does not activate."""
    g = manual_graph
    await upload(g)
    rejection = ManualPaymentReview(
        decision="reject", note="Transfer not found in the bank ledger"
    )
    async with g.sessions() as session:
        service = ManualPaymentService(session=session)
        await service.review(payment_id=g.payment, admin_id=g.reviewer, data=rejection)
        await service.review(payment_id=g.payment, admin_id=g.reviewer, data=rejection)
        with pytest.raises(ConflictError):
            await service.review(
                payment_id=g.payment, admin_id=g.reviewer, data=approval()
            )
    snapshot = await state(g)
    assert snapshot[0] == ("failed", None)
    assert snapshot[1] == ("pending", None, None)
    assert snapshot[2:] == (0, 2, "rejected")


@pytest.mark.asyncio
async def test_private_upload_download_and_admin_http_review(
    manual_graph: ManualGraph, client: AsyncClient
) -> None:
    """Ensure private upload download and admin http review."""
    g = manual_graph
    app.dependency_overrides[auth.get_current_owner] = lambda: auth.OwnerPrincipal(
        g.owner
    )
    app.dependency_overrides[auth.get_current_admin] = lambda: auth.AdminPrincipal(
        g.reviewer
    )
    response = await client.post(
        f"/api/v1/payments/{g.payment}/receipt",
        content=CONTENT,
        headers={"Content-Type": "image/png", "X-Transaction-Reference": "CCP-12345"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["review_status"] == "pending"
    review_context = await client.get(f"/api/v1/admin/manual-payments/{g.payment}")
    assert review_context.status_code == 200, review_context.text
    assert review_context.json()["payment"]["amount"] == 50
    assert review_context.json()["audit"][0]["action"] == "receipt_submitted"
    download = await client.get(f"/api/v1/payments/{g.payment}/receipt/file")
    assert download.content == CONTENT
    assert download.headers["content-disposition"].startswith("attachment;")
    assert download.headers["cache-control"] == "no-store"
    assert download.headers["x-content-type-options"] == "nosniff"
    forbidden = await client.patch(f"/api/v1/payments/{g.payment}/confirm")
    assert forbidden.status_code == 403
    result = await client.post(
        f"/api/v1/admin/manual-payments/{g.payment}/review",
        json=approval().model_dump(mode="json"),
    )
    assert result.status_code == 200, result.text
    assert result.json()["review_status"] == "approved"
    history = await client.get(f"/api/v1/admin/manual-payments/{g.payment}")
    assert history.json()["audit"][-1]["details"]["reviewer_admin_id"] == g.reviewer
    app.dependency_overrides[auth.get_current_owner] = lambda: auth.OwnerPrincipal(
        g.other_owner
    )
    assert (
        await client.get(f"/api/v1/payments/{g.payment}/receipt/file")
    ).status_code == 404


@pytest.mark.asyncio
async def test_checkout_uses_server_price_and_reuses_pending_invoice(
    manual_graph: ManualGraph, sample_restaurant_data: dict[str, Any]
) -> None:
    """Ensure checkout uses server price and reuses pending invoice."""
    g = manual_graph
    async with g.sessions() as session:
        restaurant = (
            await session.execute(
                insert(Restaurant.__table__)
                .values(
                    **dict(
                        sample_restaurant_data,
                        owner_id=g.owner,
                        name="Second billing restaurant",
                    )
                )
                .returning(Restaurant.id)
            )
        ).scalar_one()
        await session.commit()
        data = ManualSubscriptionCheckout(
            restaurant_id=restaurant, plan_id=g.plan, payment_method="baridimob"
        )
        first = await SubscriptionCheckoutService(session=session).create(
            owner_id=g.owner, data=data
        )
        second = await SubscriptionCheckoutService(session=session).create(
            owner_id=g.owner, data=data
        )
        assert first.id == second.id
        assert first.status == "pending"
        assert first.payment_provider == "manual_transfer"
        assert first.currency == "DZD"
        assert first.amount > 0
        amount = (
            await session.execute(
                select(Subscription.amount).where(
                    Subscription.id == first.subscription_id
                )
            )
        ).scalar_one()
        assert first.amount == amount


@pytest.mark.asyncio
async def test_review_refreshes_cached_rows_after_another_session_settles(
    manual_graph: ManualGraph,
) -> None:
    """Ensure review refreshes cached rows after another session settles."""
    g = manual_graph
    await upload(g)
    async with g.sessions() as stale_session:
        repository = ManualPaymentRepository(session=stale_session)
        cached_payment = await repository.get_payment(
            payment_id=g.payment, owner_id=g.owner
        )
        cached_receipt = await repository.get_receipt(payment_id=g.payment)
        assert cached_payment.status == "pending"
        assert cached_receipt.review_status == "pending"
        async with g.sessions() as writer:
            await ManualPaymentService(session=writer).review(
                payment_id=g.payment, admin_id=g.reviewer, data=approval()
            )
        committed = await state(g)
        result = await ManualPaymentService(session=stale_session).review(
            payment_id=g.payment, admin_id=g.reviewer, data=approval()
        )
        assert result.review_status == "approved"
        assert cached_payment.status == "paid"
        assert cached_receipt.review_status == "approved"
    assert await state(g) == committed
