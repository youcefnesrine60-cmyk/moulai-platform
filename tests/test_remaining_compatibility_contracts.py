# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Regression contracts for primary NLU/UI interfaces and group API removal."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agent.nlu.entity_extractor import EntityExtractor
from app.agent.nlu.intent_classifier import IntentClassifier
from app.helpers import ui_manager
from app.main import app


@pytest.mark.asyncio
async def test_intent_classifier_preserves_prompts_on_primary_chat_interface():
    chat = AsyncMock(return_value='{"intent":"greeting","confidence":0.9}')
    classifier = IntentClassifier(ai_client=SimpleNamespace(enabled=True, chat=chat))
    result = await classifier._classify_with_ai(text="hello", language="en")
    assert result["intent"] == "greeting"
    assert result["entities"] == {}
    kwargs = chat.await_args.kwargs
    assert "hello" in kwargs["message"]
    assert (
        kwargs["system_prompt"]
        == "You are an intent classifier. Output only valid JSON."
    )
    assert kwargs["temperature"] == 0.1
    assert kwargs["max_tokens"] == 200


@pytest.mark.asyncio
async def test_entity_extractor_preserves_prompts_on_primary_chat_interface():
    chat = AsyncMock(return_value="[]")
    extractor = EntityExtractor(ai_client=SimpleNamespace(enabled=True, chat=chat))
    assert await extractor._extract_with_ai(text="two pizzas", language="en") == []
    kwargs = chat.await_args.kwargs
    assert "two pizzas" in kwargs["message"]
    assert "entity extraction expert" in kwargs["system_prompt"]
    assert kwargs["temperature"] == 0.1
    assert kwargs["max_tokens"] == 500


@pytest.mark.asyncio
async def test_direct_send_keeps_keyboard_and_message_tracking(monkeypatch):
    response = {"result": {"message_id": 41}}
    send = AsyncMock(return_value=response)
    append = AsyncMock()
    monkeypatch.setattr(ui_manager, "send_message", send)
    monkeypatch.setattr(ui_manager, "append_to_state_list", append)
    markup = {"inline_keyboard": []}
    assert (
        await ui_manager.UIManager.send_new_message(
            chat_id=7, text="hello", reply_markup=markup
        )
        == response
    )
    send.assert_awaited_once_with(chat_id=7, text="hello", reply_markup=markup)
    append.assert_awaited_once_with(chat_id=7, list_key="message_ids", value=41)


@pytest.mark.asyncio
async def test_direct_edit_keeps_target_and_does_not_track_a_new_message(monkeypatch):
    edit = AsyncMock(return_value={"ok": True})
    append = AsyncMock()
    monkeypatch.setattr(ui_manager, "edit_message", edit)
    monkeypatch.setattr(ui_manager, "append_to_state_list", append)
    assert await ui_manager.UIManager.edit(
        chat_id=7, message_id=41, text="updated"
    ) == {"ok": True}
    edit.assert_awaited_once_with(
        chat_id=7, message_id=41, text="updated", reply_markup=None
    )
    append.assert_not_awaited()


def test_group_api_has_no_fictitious_status_operation_or_ignored_flags():
    paths = app.openapi()["paths"]
    base = "/api/v1/restaurant-groups"
    assert base + "/{group_id}/toggle-status" not in paths
    assert "delete" in paths[base + "/{group_id}"]
    for path, operations in paths.items():
        if path.startswith(base):
            for operation in operations.values():
                assert not {
                    "include_inactive",
                    "only_active",
                    "permanent",
                }.intersection(item["name"] for item in operation.get("parameters", []))
