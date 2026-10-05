import pytest

from app.agent.executor.actions import (
    ActionResponse,
    ComplaintAction,
    ModifyOrderAction,
)
from app.agent.prompts.templates import get_success_prompt
from app.agent.response_generator import ResponseGenerator


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action_type", "intent", "error", "messages"),
    [
        (
            ModifyOrderAction,
            "modify_order",
            "order_modification_not_supported",
            {
                "ar": "تعديل الطلبات عبر المحادثة غير متاح حالياً. لم يتم تغيير الطلب.",
                "en": "Order modifications are not available yet. The order was not changed.",
                "fr": "La modification des commandes n'est pas encore disponible. La commande n'a pas été modifiée.",
            },
        ),
        (
            ComplaintAction,
            "complaint",
            "complaint_registration_not_supported",
            {
                "ar": "تسجيل الشكاوى غير متاح حالياً. لم يتم إنشاء بلاغ.",
                "en": "Complaint registration is not available yet. No ticket was created.",
                "fr": "L'enregistrement des réclamations n'est pas encore disponible. Aucun ticket n'a été créé.",
            },
        ),
    ],
)
@pytest.mark.parametrize("language", ["ar", "en", "fr"])
async def test_unavailable_actions_report_failure_without_claiming_success(
    action_type,
    intent,
    error,
    messages,
    language,
):
    action_result = await action_type().execute(params={})
    response = await ResponseGenerator(use_ai=False).generate(
        intent=intent,
        language=language,
        action_result=action_result,
    )

    assert action_result.success is False
    assert action_result.error == error
    assert response == messages[language]


def test_unknown_success_prompt_does_not_fall_back_to_order_created():
    response = get_success_prompt("order_updated", language="en")

    assert "created successfully" not in response
    assert "updated successfully" not in response
