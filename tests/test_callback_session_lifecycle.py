# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Execute previously broken callback reads using a coroutine session factory."""

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


@pytest.mark.asyncio
async def test_subscription_pricing_uses_active_session_and_naive_utc_dates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Subscription pricing reads metrics in a live session using normalized UTC."""
    module = subscription_step
    sessions = install_sessions(monkeypatch, module)
    # Database columns store UTC without timezone information.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    monkeypatch.setattr(
        module,
        "get_state",
        AsyncMock(return_value={"restaurant_id": 15, "owner_id": 4}),
    )
    monkeypatch.setattr(module, "set_state", AsyncMock())
    monkeypatch.setattr(module.UIManager, "send_new_message", AsyncMock())
    monkeypatch.setattr(
        module, "ProductRepository", lambda s: repository(s, count_by_restaurant=3)
    )
    monkeypatch.setattr(
        module, "CategoriesRepository", lambda s: repository(s, get_by_restaurant_id=[])
    )
    monkeypatch.setattr(
        module, "BranchesRepository", lambda s: repository(s, count_by_restaurant=1)
    )
    monkeypatch.setattr(
        module,
        "RestaurantRepository",
        lambda s: repository(s, get_by_owner_id=[object()]),
    )
    monkeypatch.setattr(
        module,
        "OwnerService",
        lambda session: repository(session, get_created_at=now - timedelta(days=730)),
    )
    monkeypatch.setattr(
        module,
        "OrdersRepository",
        lambda s: repository(
            s,
            get_by_restaurant_id=[
                SimpleNamespace(
                    created_at=now - timedelta(days=1),
                    status="completed",
                    total_amount=25,
                )
            ],
        ),
    )
    calls: list[dict[str, Any]] = []

    async def price(*, session: Session, **values: Any) -> dict[str, int]:
        """Capture business metrics while the pricing session remains active."""
        assert session.active
        calls.append(values)
        return {"final_amount_due": 50}

    monkeypatch.setattr(module, "calculate_subscription_pricing", price)
    await module.calculate_subscription_price_for_owner(chat_id=7, plan_id=2)
    assert calls[0]["years_with_platform"] == 2
    assert calls[0]["monthly_orders"] == 1
    assert calls[0]["average_order_value"] == 25
    assert all(s.closed for s in sessions)
