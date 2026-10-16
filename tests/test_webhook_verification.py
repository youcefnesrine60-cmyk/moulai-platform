# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Telegram webhook authentication and callback routing contracts."""

import inspect
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import (
    ASGITransport,
    AsyncClient,
)
from pydantic import SecretStr

from app.api import webhook
from app.core.callback_router import CallbackRouter
from app.handlers import callback_routes
from app.handlers.callbacks.payment import router as payment_router
from app.services.telegram import webhook as telegram_registration


@pytest.mark.asyncio
async def test_payment_routes_select_confirm_and_navigate_without_gateway_handlers(
    monkeypatch,
):
    router = CallbackRouter()
    handlers = {
        name: AsyncMock()
        for name in [
            "payment_method_callback",
            "payment_confirm_callback",
            "retry_payment_callback",
            "back_to_payment_callback",
        ]
    }
    monkeypatch.setattr(payment_router, "router", router)
    for name, handler in handlers.items():
        monkeypatch.setattr(payment_router, name, handler)
    await payment_router.register_payment_routes()
    for data, name in [
        ("payment_card_15", "payment_method_callback"),
        ("payment_confirm_15", "payment_confirm_callback"),
        ("retry_payment_15", "retry_payment_callback"),
        ("back_to_payment_15", "back_to_payment_callback"),
    ]:
        await router.dispatch(callback_data=data, chat_id=7, message_id=8)
        assert handlers[name].await_args.kwargs["match"].group(1) == "15"
    before = sum(handler.await_count for handler in handlers.values())
    await router.dispatch(
        callback_data="payment_success_pi_forged", chat_id=7, message_id=8
    )
    await router.dispatch(
        callback_data="payment_failure_pi_forged", chat_id=7, message_id=8
    )
    assert sum(handler.await_count for handler in handlers.values()) == before


@pytest.mark.asyncio
async def test_full_router_contracts_and_single_payment_registration(monkeypatch):
    from app.core import router_instance

    # Registration modules share the same singleton; replace only route storage.
    monkeypatch.setattr(router_instance.router, "routes", [])
    await callback_routes.setup_routes()
    routes = router_instance.router.routes
    for regex, handler in routes:
        inspect.signature(handler).bind(
            chat_id=7, message_id=8, callback_data="test", match=regex.match("test")
        )
    assert sum(regex.pattern == r"^payment_confirm_(\d+)$" for regex, _ in routes) == 1
    assert not any(
        regex.match("payment_success_pi_forged")
        or regex.match("payment_failure_pi_forged")
        for regex, _ in routes
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case,expected", [("disabled", 503), ("wrong", 403), ("valid", 200)]
)
async def test_telegram_requires_configured_secret_before_dispatch(
    monkeypatch, case, expected
):
    app = FastAPI()
    app.include_router(webhook.router)
    secret = "test_token_123"
    monkeypatch.setattr(
        webhook.settings,
        "TELEGRAM_WEBHOOK_SECRET_TOKEN",
        None if case == "disabled" else SecretStr(secret),
    )
    dispatch = AsyncMock()
    monkeypatch.setattr(webhook, "dispatch_update", dispatch)
    monkeypatch.setattr(webhook.RequestLogger, "log", AsyncMock())
    monkeypatch.setattr(
        webhook.GatewayMiddleware, "process", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(webhook.RiskEngine, "analyze", AsyncMock(return_value=True))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/webhook",
            json={"message": {"chat": {"id": 7}, "text": "hello"}},
            headers={
                "X-Telegram-Bot-Api-Secret-Token": secret
                if case == "valid"
                else "forged"
            },
        )
    assert response.status_code == expected
    if case == "valid":
        dispatch.assert_awaited_once()
    else:
        dispatch.assert_not_awaited()


@pytest.mark.asyncio
async def test_telegram_registration_sends_secret_without_live_request(monkeypatch):
    post = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(telegram_registration, "_post", post)
    monkeypatch.setattr(
        telegram_registration.settings,
        "TELEGRAM_WEBHOOK_SECRET_TOKEN",
        SecretStr("local_test_token"),
    )
    await telegram_registration.set_webhook(url="https://example.invalid/webhook")
    post.assert_awaited_once_with(
        method="setWebhook",
        data={
            "url": "https://example.invalid/webhook",
            "secret_token": "local_test_token",
        },
    )
