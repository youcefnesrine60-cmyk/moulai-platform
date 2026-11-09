# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# CALLBACK SESSION LIFECYCLE
# Verify active database-session boundaries and authoritative pricing-input delegation offline.
# ==============================================

"""Execute previously broken callback reads using a coroutine session factory."""

# isort: split
# ==============================================
# IMPORTS
# Declare the local framework, schema and contract dependencies used in this file.
# ==============================================

import re
from collections.abc import (
    Awaitable,
    Callable,
)
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from types import (
    ModuleType,
    SimpleNamespace,
)
from typing import (
    Any,
    Self,
    TypeAlias,
)
from unittest.mock import AsyncMock

import pytest

from app.handlers.callbacks.customer import restaurant_details as selection
from app.handlers.callbacks.owner import owner_dashboard_handlers as owner
from app.handlers.callbacks.restaurant import (
    details,
    menu,
)
from app.handlers.owner_handler import subscription_step
from app.services.business import subscription_metrics
from app.services.business.subscription_types import (
    PricingInputs,
    ReferenceMetrics,
)

Callback: TypeAlias = Callable[..., Awaitable[Any]]


class Session:
    """Track the lifecycle of a context-managed offline session."""

    def __init__(self) -> None:
        """Initialize the session before entering its asynchronous scope."""
        self.active = False
        self.closed = False

    async def __aenter__(self) -> Self:
        """Mark the session active during repository operations."""
        self.active = True
        return self

    async def __aexit__(self, *args: object) -> None:
        """Record cleanup on successful or failed callback completion."""
        self.active = False
        self.closed = True


def install_sessions(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
) -> list[Session]:
    """Install the coroutine-shaped session factory used by callback handlers."""
    sessions: list[Session] = []

    async def factory() -> Session:
        """Create a fresh tracked session for each callback invocation."""
        session = Session()
        sessions.append(session)
        return session

    monkeypatch.setattr(module, "get_session", factory)
    return sessions


def repository(session: Session, **methods: Any) -> SimpleNamespace:
    """Expose mocked methods only while the database session is active."""
    assert session.active
    return SimpleNamespace(
        **{name: AsyncMock(return_value=value) for name, value in methods.items()}
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("module", [menu, details, selection])
async def test_public_restaurant_reads_await_session_and_close_it(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
) -> None:
    """Public catalog callbacks await session creation and always release it."""
    sessions = install_sessions(monkeypatch, module)
    edit = AsyncMock()
    monkeypatch.setattr(module.UIManager, "edit", edit)
    if module is menu:
        monkeypatch.setattr(
            menu,
            "CategoriesRepository",
            lambda s: repository(
                s, get_by_restaurant_id=[SimpleNamespace(id=2, name="Menu")]
            ),
        )
        monkeypatch.setattr(
            menu,
            "ProductRepository",
            lambda s: repository(
                s,
                get_by_restaurant_id=[
                    SimpleNamespace(category_id=2, name="Pizza", price=25)
                ],
            ),
        )
        callback = menu.restaurant_menu_callback.__wrapped__
    else:
        monkeypatch.setattr(
            module,
            "RestaurantRepository",
            lambda s: repository(
                s,
                get_by_id=SimpleNamespace(
                    name="Restaurant", phone="123", wilaya="Alger"
                ),
            ),
        )
        if module is details:
            monkeypatch.setattr(
                details,
                "BranchesRepository",
                lambda s: repository(s, get_by_restaurant_id=[]),
            )
            monkeypatch.setattr(
                details,
                "ProductRepository",
                lambda s: repository(s, count_by_restaurant=3),
            )
            callback = details.restaurant_details_callback.__wrapped__
        else:
            callback = selection.handle_restaurant_selection
    await callback(
        chat_id=7,
        message_id=8,
        callback_data="rest_15",
        match=re.match(r"rest_(\d+)", "rest_15"),
    )
    assert sessions and all(s.closed for s in sessions)
    edit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "callback",
    [
        owner.owner_dashboard_callback,
        owner.owner_orders_callback,
        owner.owner_products_callback,
    ],
)
@pytest.mark.parametrize("allowed", [False, True])
async def test_owner_reads_check_ownership_and_close_sessions(
    monkeypatch: pytest.MonkeyPatch,
    callback: Callback,
    allowed: bool,
) -> None:
    """Owner callbacks reject foreign restaurants before reading their data."""
    sessions = install_sessions(monkeypatch, owner)
    monkeypatch.setattr(
        owner,
        "OwnerRepository",
        lambda session: repository(session, get_by_chat_id=SimpleNamespace(id=4)),
    )
    monkeypatch.setattr(
        owner,
        "RestaurantRepository",
        lambda s: repository(
            s,
            get_by_id=SimpleNamespace(
                id=15, name="Restaurant", owner_id=4 if allowed else 99
            ),
        ),
    )
    orders = AsyncMock(return_value=[])
    products = AsyncMock(return_value=0)
    monkeypatch.setattr(
        owner,
        "OrdersRepository",
        lambda s: SimpleNamespace(get_by_restaurant_id=orders) if s.active else None,
    )
    monkeypatch.setattr(
        owner,
        "ProductRepository",
        lambda s: SimpleNamespace(count_by_restaurant=products) if s.active else None,
    )
    monkeypatch.setattr(
        owner, "CategoriesRepository", lambda s: repository(s, get_by_restaurant_id=[])
    )
    monkeypatch.setattr(owner, "get_state", AsyncMock(return_value={}))
    monkeypatch.setattr(owner, "set_state", AsyncMock())
    monkeypatch.setattr(owner.UIManager, "edit", AsyncMock())
    monkeypatch.setattr(owner, "owner_dashboard_ui", AsyncMock(return_value={}))
    await callback.__wrapped__(
        chat_id=7,
        message_id=8,
        callback_data="owner_15",
        match=re.match(r"owner_(\d+)", "owner_15"),
    )
    assert all(s.closed for s in sessions)
    if not allowed:
        orders.assert_not_awaited()
        products.assert_not_awaited()
        owner.set_state.assert_not_awaited()
    elif callback is owner.owner_products_callback:
        products.assert_awaited_once()
    else:
        orders.assert_awaited_once()


# ==============================================
# VERIFIED PRICING INPUTS WITH ONE ACTIVE SESSION
# The callback delegates paid-history rules instead of estimating tenure from account creation.
# ==============================================


@pytest.mark.asyncio
async def test_subscription_pricing_uses_active_session_and_verified_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass authoritative inputs unchanged, then close the session before rendering UI."""
    module = subscription_step
    sessions = install_sessions(monkeypatch, module)
    state = {"restaurant_id": 15, "owner_id": 4}
    monkeypatch.setattr(module, "get_state", AsyncMock(return_value=state))
    save = AsyncMock()
    send = AsyncMock()
    monkeypatch.setattr(module, "set_state", save)
    monkeypatch.setattr(module.UIManager, "send_new_message", send)
    inputs: PricingInputs = {
        "products_count": 3,
        "categories_count": 0,
        "branches_count": 1,
        "restaurants_count": 1,
        "years_with_platform": 2,
        "monthly_orders": 1,
        "average_order_value": Decimal("25.37"),
    }
    metric_sessions: list[Session] = []
    calls: list[dict[str, object]] = []

    async def metrics(
        *, session: Session, owner_id: int, restaurant_id: int, now: datetime
    ) -> tuple[ReferenceMetrics, PricingInputs]:
        """Keep the UTC clock at the service boundary and return verified historical data."""
        assert session.active
        assert owner_id == 4 and restaurant_id == 15
        assert now.tzinfo is timezone.utc
        metric_sessions.append(session)
        end = now.replace(tzinfo=None)
        reference: ReferenceMetrics = {
            "products_count": inputs["products_count"],
            "categories_count": inputs["categories_count"],
            "monthly_orders": inputs["monthly_orders"],
            "average_order_value": inputs["average_order_value"],
            "reference_start": end - timedelta(days=30),
            "reference_end": end,
            "source_subscription_id": 99,
            "context": "renewal",
        }
        return reference, inputs

    async def price(*, session: Session, **values: object) -> dict[str, Decimal]:
        """Require the same session and preserve the exact Decimal inputs."""
        assert session.active and session is metric_sessions[0]
        calls.append(values)
        return {"final_amount_due": Decimal("50.00")}

    monkeypatch.setattr(subscription_metrics, "pricing_inputs", metrics)
    monkeypatch.setattr(module, "calculate_subscription_pricing", price)
    await module.calculate_subscription_price_for_owner(chat_id=7, plan_id=2)
    assert calls == [
        {
            "plan_id": 2,
            "billing_cycle": "monthly",
            "payment_method": "electronic",
            "owner_id": 4,
            "restaurant_id": 15,
            **inputs,
        }
    ]
    assert len(sessions) == 1 and all(session.closed for session in sessions)
    assert state["selected_plan_id"] == 2
    assert state["pricing_result"] == {"final_amount_due": Decimal("50.00")}
    save.assert_awaited_once_with(chat_id=7, state=state)
    send.assert_awaited_once()
