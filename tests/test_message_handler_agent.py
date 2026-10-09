# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# TEST MODULE - TESTS / TEST MESSAGE HANDLER AGENT
# Automated test coverage for the MoulAI platform.
# ==============================================

"""Automated tests for test message handler agent.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import pytest

from app.agent.executor.action_executor import ActionExecutor
from app.agent.executor.actions import (
    ActionRegistry,
    ActionResponse,
    BaseAction,
    OrderFoodAction,
)
from app.handlers import message_handler

# ==============================================
# TEST MESSAGE WITHOUT STATE USES AGENT AND SENDS RESPONSE
# ==============================================


@pytest.mark.asyncio
async def test_message_without_state_uses_agent_and_sends_response(monkeypatch):
    calls = {}
    sent = {}

    # ==============================================
    # CAPTCHA NOT REQUIRED
    # ==============================================

    async def captcha_not_required(*, chat_id):
        return False

    # ==============================================
    # STORE MESSAGE ID
    # ==============================================

    async def store_message_id(**kwargs):
        return None

    # ==============================================
    # NO STATE
    # ==============================================

    async def no_state(*, chat_id):
        return None

    # ==============================================
    # PROCESS
    # ==============================================

    async def process(**kwargs):
        calls.update(kwargs)
        return {"response": "Agent response"}

    # ==============================================
    # SEND
    # ==============================================

    async def send(**kwargs):
        sent.update(kwargs)

    monkeypatch.setattr(
        message_handler.CaptchaManager, "is_required", captcha_not_required
    )
    monkeypatch.setattr(message_handler, "append_to_state_list", store_message_id)
    monkeypatch.setattr(message_handler, "get_state", no_state)
    monkeypatch.setattr(message_handler.agent_engine, "process", process)
    monkeypatch.setattr(message_handler, "send_message", send)

    await message_handler.handle_message(
        data={
            "message": {
                "chat": {"id": 42},
                "message_id": 7,
                "text": "Bonjour",
            },
        },
    )

    assert calls["user_id"] == 42
    assert calls["message"] == "Bonjour"
    assert calls["session_id"] == "telegram_42"
    assert sent == {"chat_id": 42, "text": "Agent response"}


# ==============================================
# TEST CUSTOMER FREE TEXT USES AGENT WITH SELECTED RESTAURANT
# ==============================================


@pytest.mark.asyncio
async def test_customer_free_text_uses_agent_with_selected_restaurant(monkeypatch):
    calls = {}

    # ==============================================
    # CAPTCHA NOT REQUIRED
    # ==============================================

    async def captcha_not_required(*, chat_id):
        return False

    # ==============================================
    # STORE MESSAGE ID
    # ==============================================

    async def store_message_id(**kwargs):
        return None

    # ==============================================
    # CUSTOMER STATE
    # ==============================================

    async def customer_state(*, chat_id):
        return {"flow": "customer", "step": "product", "restaurant_id": 9}

    # ==============================================
    # PROCESS
    # ==============================================

    async def process(**kwargs):
        calls.update(kwargs)
        return {"response": "Menu"}

    # ==============================================
    # SEND
    # ==============================================

    async def send(**kwargs):
        return None

    # ==============================================
    # DISPATCH
    # ==============================================

    async def dispatch(**kwargs):
        pytest.fail("free text should not be parsed as a numeric checkout selection")

    monkeypatch.setattr(
        message_handler.CaptchaManager, "is_required", captcha_not_required
    )
    monkeypatch.setattr(message_handler, "append_to_state_list", store_message_id)
    monkeypatch.setattr(message_handler, "get_state", customer_state)
    monkeypatch.setattr(message_handler.StateDispatcher, "dispatch", dispatch)
    monkeypatch.setattr(message_handler.agent_engine, "process", process)
    monkeypatch.setattr(message_handler, "send_message", send)

    await message_handler.handle_message(
        data={
            "message": {
                "chat": {"id": 42},
                "message_id": 8,
                "text": "أرني القائمة",
            },
        },
    )

    assert calls["context"] == {"chat_id": 42, "restaurant_id": 9}


# ==============================================
# TEST ORDER ACTION WAITS FOR EXPLICIT CONFIRMATION
# ==============================================


@pytest.mark.asyncio
async def test_order_action_waits_for_explicit_confirmation():
    executed = False

    class ConfirmAction(BaseAction):
        # ==============================================
        #   INIT
        # ==============================================

        def __init__(self):
            super().__init__(name="order_food", requires_confirmation=True)

        # ==============================================
        # EXECUTE
        # ==============================================

        async def execute(self, *, params, context=None):
            nonlocal executed
            executed = True
            return ActionResponse(success=True, message="created")

    registry = ActionRegistry()
    registry.register(ConfirmAction())
    executor = ActionExecutor(registry=registry)

    result = await executor.execute(
        intent_result={
            "intent": "order_food",
            "confidence": 1.0,
            "entities": {"product_name": "Pizza", "quantity": 1},
            "language": "en",
        },
        context={"user_id": 42},
    )

    assert result["data"]["pending_confirmation"] is True
    assert result["confirmed"] is False
    assert executed is False


# ==============================================
# TEST ORDER ACTION WITHOUT PRODUCT DOES NOT CLAIM SUCCESS
# ==============================================


@pytest.mark.asyncio
async def test_order_action_without_product_does_not_claim_success():
    result = await OrderFoodAction().prepare(params={}, context={"user_id": 42})

    assert result.success is False
    assert result.error == "missing_order_details"
