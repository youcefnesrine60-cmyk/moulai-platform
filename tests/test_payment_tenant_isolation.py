# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PAYMENT TENANT ISOLATION CONTRACTS
# Regression coverage for owner and restaurant payment boundaries.
# ==============================================

"""Verify that payment entry points cannot cross tenant boundaries."""

import inspect
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.auth import OwnerPrincipal
from app.api.v1 import payments
from app.services.business.orders import paid


class _PaymentRepository:
    """Minimal repository double recording the scoped list filter."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(self) -> None:
        self.filters: dict[str, object] | None = None

    # ==============================================
    # GET ALL
    # ==============================================

    async def get_all(
        self,
        *,
        skip: int,
        limit: int,
        filters: dict[str, object],
    ) -> list[object]:
        self.filters = filters
        return []

    # ==============================================
    # COUNT
    # ==============================================

    async def count(self, *, filters: dict[str, object]) -> int:
        assert filters == self.filters
        return 0


# ==============================================
# TEST PAYMENT LOOKUP CHECKS OWNER BEFORE SERVICE ACCESS
# ==============================================


@pytest.mark.asyncio
async def test_payment_lookup_checks_owner_before_service_access(monkeypatch) -> None:
    """A foreign payment identifier must be rejected before it reaches the service."""

    # ==============================================
    # REJECT FOREIGN PAYMENT
    # ==============================================

    async def reject_foreign_payment(**_: object) -> None:
        raise HTTPException(status_code=404, detail="Payment not found")

    class Service:
        session = object()

        # ==============================================
        # GET BY ID
        # ==============================================

        async def get_by_id(self, *, payment_id: int) -> object:
            raise AssertionError(f"service accessed foreign payment {payment_id}")

    monkeypatch.setattr(payments, "require_owned_payment", reject_foreign_payment)

    with pytest.raises(HTTPException, match="Payment not found"):
        await payments.get_payment(
            owner=OwnerPrincipal(owner_id=9),
            payment_id=42,
            service=Service(),
        )


# ==============================================
# TEST PAYMENT LIST FORCES AUTHENTICATED OWNER SCOPE
# ==============================================


@pytest.mark.asyncio
async def test_payment_list_forces_authenticated_owner_scope() -> None:
    """Client filters can never broaden a payment list beyond the authenticated owner."""

    repository = _PaymentRepository()
    service = SimpleNamespace(session=object(), repo=repository)

    result = await payments.list_payments(
        owner=OwnerPrincipal(owner_id=9),
        owner_id=None,
        restaurant_id=None,
        status="paid",
        skip=0,
        limit=20,
        service=service,
    )

    assert result.total == 0
    assert repository.filters == {"owner_id": 9, "status": "paid"}


# ==============================================
# TEST PAYMENT ENTRY POINTS REQUIRE TENANT CONTEXT
# ==============================================


def test_payment_entry_points_require_tenant_context() -> None:
    """Public payment operations must declare the owner or restaurant boundary."""

    endpoint_names = (
        "list_payments",
        "get_payment",
        "get_payment_status",
        "create_payment",
        "update_payment",
        "update_payment_status",
        "confirm_payment",
        "fail_payment",
        "cancel_payment",
        "refund_payment",
        "delete_payment",
        "get_payment_summary",
        "get_subscription_payments",
    )
    for endpoint_name in endpoint_names:
        assert "owner" in inspect.signature(getattr(payments, endpoint_name)).parameters

    order_payment_names = (
        "mark_order_paid",
        "is_order_paid",
        "get_order_payment_status",
        "unpay_order",
        "process_order_payment",
    )
    for function_name in order_payment_names:
        assert (
            "restaurant_id"
            in inspect.signature(getattr(paid, function_name)).parameters
        )
