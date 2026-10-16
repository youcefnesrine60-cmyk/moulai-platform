# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Callback contracts for explicit SQLAlchemy sessions and payment domains."""

import re
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import NotFoundError
from app.handlers.callbacks.customer import payment as customer
from app.handlers.customer_handler import checkout_step


class ManagedSession:
    def __init__(self):
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["valid", "foreign", "disabled-method"])
async def test_selection_displays_persisted_amount_after_customer_scope(
    monkeypatch, case
):
    session = ManagedSession()
    state = {"cart": [{"price": 0.01}], "total_amount": 0.01}
    options = AsyncMock(return_value=(25, {"cash"} if case == "valid" else set()))
    if case == "foreign":
        options.side_effect = NotFoundError(message="Order not found")
    save, edit, ui = AsyncMock(), AsyncMock(), AsyncMock(return_value={})
    monkeypatch.setattr(customer, "get_session", AsyncMock(return_value=session))
    monkeypatch.setattr(customer, "get_state", AsyncMock(return_value=state))
    monkeypatch.setattr(customer, "set_state", save)
    monkeypatch.setattr(customer.UIManager, "edit", edit)
    monkeypatch.setattr(customer, "payment_confirmation_ui", ui)
    monkeypatch.setattr(
        customer,
        "OrderPaymentsService",
        lambda *, session: SimpleNamespace(get_customer_payment_options=options),
    )
    await customer.payment_method_callback.__wrapped__(
        chat_id=82001,
        message_id=41,
        callback_data="payment_cash_15",
        match=re.match(r"payment_(?:cash)_(\d+)", "payment_cash_15"),
    )
    assert session.closed
    options.assert_awaited_once_with(chat_id=82001, order_id=15)
    if case == "valid":
        assert state["total_amount"] == 25
        ui.assert_awaited_once_with(order_id=15, payment_method="cash", amount=25)
        save.assert_awaited_once()
    else:
        save.assert_not_awaited()
        ui.assert_not_awaited()
        assert "payment_method" not in state


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "callback", [customer.retry_payment_callback, customer.back_to_payment_callback]
)
@pytest.mark.parametrize("allowed", [False, True])
async def test_payment_navigation_checks_customer_without_overwriting_status(
    monkeypatch, callback, allowed
):
    session = ManagedSession()
    state = {"payment_status": "paid", "total_amount": 0.01}
    options = AsyncMock(return_value=(25, {"cash"}))
    if not allowed:
        options.side_effect = NotFoundError(message="Order not found")
    save, ui = AsyncMock(), AsyncMock(return_value={})
    monkeypatch.setattr(customer, "get_session", AsyncMock(return_value=session))
    monkeypatch.setattr(customer, "get_state", AsyncMock(return_value=state))
    monkeypatch.setattr(customer, "set_state", save)
    monkeypatch.setattr(customer.UIManager, "edit", AsyncMock())
    monkeypatch.setattr(customer, "payment_ui", ui)
    monkeypatch.setattr(
        customer,
        "OrderPaymentsService",
        lambda *, session: SimpleNamespace(get_customer_payment_options=options),
    )
    await callback.__wrapped__(
        chat_id=82001,
        message_id=41,
        callback_data="navigate_15",
        match=re.match(r"navigate_(\d+)", "navigate_15"),
    )
    assert session.closed
    assert state["payment_status"] == "paid"
    if allowed:
        assert state["total_amount"] == 25
        ui.assert_awaited_once_with(order_id=15, allowed_methods={"cash"})
    else:
        save.assert_not_awaited()
        ui.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("fails", [False, True])
@pytest.mark.parametrize("status", ["pending", "paid"])
async def test_customer_confirmation_uses_order_service_and_persisted_amount(
    monkeypatch, fails, status
):
    session = ManagedSession()
    state = {
        "payment_method": "cash",
        "total_amount": 0.01,
        "owner_id": 999,
        "restaurant_id": 999,
    }
    confirm = AsyncMock(
        return_value=SimpleNamespace(
            id=31, amount=25, payment_status=status, payment_method="cash"
        )
    )
    if fails:
        confirm.side_effect = ValueError("payment denied")
    save = AsyncMock()
    success_ui = AsyncMock(return_value={})
    expected_session = session
    monkeypatch.setattr(customer, "get_session", AsyncMock(return_value=session))
    monkeypatch.setattr(customer, "get_state", AsyncMock(return_value=state))
    monkeypatch.setattr(customer, "set_state", save)
    monkeypatch.setattr(
        customer,
        "OrderPaymentsService",
        lambda *, session: (
            SimpleNamespace(submit_customer_payment=confirm)
            if session is expected_session
            else None
        ),
    )
    monkeypatch.setattr(customer.UIManager, "edit", AsyncMock())
    pending_ui = AsyncMock(return_value={})
    monkeypatch.setattr(customer, "payment_pending_ui", pending_ui)
    monkeypatch.setattr(customer, "payment_success_ui", success_ui)
    monkeypatch.setattr(customer, "payment_failed_ui", AsyncMock(return_value={}))
    await customer.payment_confirm_callback.__wrapped__(
        chat_id=82001,
        message_id=41,
        callback_data="confirm_15",
        match=re.match(r"confirm_(\d+)", "confirm_15"),
    )
    confirm.assert_awaited_once_with(chat_id=82001, order_id=15, payment_method="cash")
    assert session.closed
    if fails:
        save.assert_not_awaited()
        success_ui.assert_not_awaited()
        assert "payment_id" not in state
    else:
        assert state["payment_id"] == 31
        assert state["total_amount"] == 25
        assert state["payment_status"] == status
        save.assert_awaited_once_with(chat_id=82001, state=state)
        if status == "paid":
            success_ui.assert_awaited_once_with(
                order_id=15, payment_method="cash", amount=25
            )
            pending_ui.assert_not_awaited()
        else:
            success_ui.assert_not_awaited()
            pending_ui.assert_awaited_once_with(order_id=15)


@pytest.mark.asyncio
@pytest.mark.parametrize("order_id", [None, 15])
async def test_checkout_reads_real_payment_settings_without_default_override(
    monkeypatch, order_id
):
    session = ManagedSession()
    service = SimpleNamespace(
        get_allowed_methods_for_order=AsyncMock(return_value=set()),
        get_allowed_methods_by_restaurant=AsyncMock(return_value=set()),
    )
    ui = AsyncMock(return_value={})
    monkeypatch.setattr(checkout_step, "get_session", AsyncMock(return_value=session))
    monkeypatch.setattr(
        checkout_step, "OrderPaymentsService", lambda *, session: service
    )
    monkeypatch.setattr(checkout_step, "payment_ui", ui)
    monkeypatch.setattr(checkout_step.UIManager, "send_new_message", AsyncMock())
    state = {"cart": [{"price": 25}], "restaurant_id": 7}
    if order_id is not None:
        state["order_id"] = order_id
    await checkout_step.handle_checkout_step(chat_id=82001, text="pay", state=state)
    if order_id is None:
        service.get_allowed_methods_by_restaurant.assert_awaited_once_with(
            restaurant_id=7
        )
        service.get_allowed_methods_for_order.assert_not_awaited()
    else:
        service.get_allowed_methods_for_order.assert_awaited_once_with(order_id=15)
        service.get_allowed_methods_by_restaurant.assert_not_awaited()
    ui.assert_awaited_once_with(allowed_methods=set(), order_id=order_id or 0)
    assert session.closed
