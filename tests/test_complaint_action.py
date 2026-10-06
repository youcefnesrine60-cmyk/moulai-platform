from types import SimpleNamespace

import pytest

from app.agent.executor import actions
from app.agent.executor.actions import ActionResponse, ComplaintAction
from app.agent.prompts.templates import get_success_prompt
from app.agent.response_generator import ResponseGenerator


@pytest.mark.asyncio
async def test_complaint_prepare_uses_message_and_requires_confirmation():
    action = ComplaintAction()

    preview = await action.prepare(
        params={"language": "en", "order_id": "RST1-000017"},
        context={"message": "The delivery arrived cold."},
    )

    assert preview.success is True
    assert preview.data == {"description": "The delivery arrived cold."}
    assert "Confirm? (Yes/No)" in preview.message


@pytest.mark.asyncio
async def test_complaint_prepare_rejects_missing_description():
    preview = await ComplaintAction().prepare(params={}, context={})

    assert preview.success is False
    assert preview.error == "complaint_description_required"


@pytest.mark.asyncio
async def test_complaint_action_persists_with_authenticated_customer_and_context_tenant(monkeypatch):
    calls = {}
    session = object()

    class SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    async def create_complaint(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(id=36)

    monkeypatch.setattr(actions, "AsyncSessionLocal", SessionContext)
    monkeypatch.setattr(actions, "create_customer_complaint", create_complaint)

    result = await ComplaintAction().execute(
        params={"description": "The food arrived cold.", "language": "en"},
        context={
            "user_id": 123,
            "request_context": {"restaurant_id": 8},
        },
    )

    assert result.success is True
    assert result.data == {"complaint_id": 36}
    assert calls["chat_id"] == 123
    assert calls["restaurant_id"] == 8
    assert calls["description"] == "The food arrived cold."
    assert calls["session"] is session


@pytest.mark.asyncio
async def test_pending_confirmation_is_not_rendered_as_completed_success():
    message = "I will register this complaint. Confirm?"

    response = await ResponseGenerator(use_ai=False).generate(
        intent="complaint",
        language="en",
        action_result=ActionResponse(
            success=True,
            message=message,
            data={"pending_confirmation": True},
        ),
    )

    assert response == message
    assert "Ticket number" not in response


def test_complaint_success_prompt_is_localized():
    response = get_success_prompt(
        "complaint_registered",
        language="fr",
        complaint_id=36,
    )

    assert "36" in response
    assert "enregistrée" in response
