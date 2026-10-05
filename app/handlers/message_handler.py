# ==============================================
# 💬 MESSAGE HANDLER - VERSION PRO
# ==============================================

from app.core.logger import logger
from app.core.state_dispatcher import StateDispatcher
from app.core.security.captcha_manager import CaptchaManager
from app.agent.engine import agent_engine

from app.handlers.captcha_handler import handle_captcha

from app.helpers.ui_helpers import send_main_menu
from app.helpers.navigation import go_back
from app.helpers.state_helper import (
    append_to_state_list,
)
from app.helpers.ui_manager import UIManager

from app.repositories.state_repo import (
    delete_state,
    get_state,
    set_state,
)
from app.agent.executor.actions import action_registry
from app.services.telegram import delete_message
from app.services.telegram import send_message
from app.states.owner_states import OwnerStates


# ==============================================
# 💬 HANDLE MESSAGE
# ==============================================

async def handle_message(
    *,
    data: dict,
) -> None:

    message = data["message"]
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    text = message.get("text", "").strip()

    logger.info(
        "message_received",
        extra={
            "chat_id": chat_id,
            "text_length": len(text),
        },
    )

    # ==========================================
    # 🤖 CAPTCHA VERIFICATION
    # ==========================================

    if await CaptchaManager.is_required(chat_id=chat_id):
        solved = await handle_captcha(
            chat_id=chat_id,
            text=text,
        )
        if not solved:
            return

    # ==========================================
    # 💾 STORE USER MESSAGE ID (دائماً)
    # ==========================================

    await append_to_state_list(
        chat_id=chat_id,
        list_key="message_ids",
        value=message_id,
    )

    logger.debug(
        "user_message_id_stored",
        extra={
            "chat_id": chat_id,
            "message_id": message_id,
        },
    )

    # ==========================================
    # 🚀 START COMMAND
    # ==========================================

    if text == "/start":
        logger.info(
            "start_command",
            extra={
                "chat_id": chat_id,
            },
        )

        await UIManager.cleanup_messages(chat_id=chat_id)

        await send_main_menu(
            chat_id=chat_id,
            message_id=None,
            cleanup=False,
        )
        return

    # ==========================================
    # 🔙 BACK BUTTON
    # ==========================================

    if text == "🔙 رجوع":
        logger.info(
            "back_requested",
            extra={
                "chat_id": chat_id,
            },
        )

        previous = await go_back(chat_id=chat_id)

        if previous is None:
            try:
                await delete_state(chat_id=chat_id)
            except Exception as e:
                logger.exception(
                    "state_cleanup_failed",
                    extra={
                        "chat_id": chat_id,
                        "error": str(e),
                    },
                )

            await UIManager.cleanup_messages(chat_id=chat_id)

            await send_main_menu(
                chat_id=chat_id,
                message_id=None,
                cleanup=False,
            )
        return

    # ==========================================
    # 📥 LOAD USER STATE
    # ==========================================

    state = await get_state(chat_id=chat_id)

    if state and state.get("flow") == "agent_confirmation":
        answer = text.casefold().strip()
        if answer in {"نعم", "اي", "أيوه", "yes", "oui", "ok", "okay", "d'accord"}:
            action = action_registry.get(state.get("action", ""))
            resume_state = state.get("resume_state")
            if resume_state:
                await set_state(chat_id=chat_id, state=resume_state)
            else:
                await delete_state(chat_id=chat_id)
            if not action:
                await send_message(
                    chat_id=chat_id,
                    text="تعذر تنفيذ العملية. الرجاء المحاولة مجدداً.",
                )
                return
            try:
                result = await action.execute(
                    params=state.get("params", {}),
                    context=state.get("context", {}),
                )
                await send_message(chat_id=chat_id, text=result.message)
            except Exception:
                logger.exception(
                    "agent_confirmed_action_failed",
                    extra={"chat_id": chat_id, "action": action.name},
                )
                await send_message(
                    chat_id=chat_id,
                    text="تعذر تنفيذ العملية. لم يتم تأكيد نجاحها.",
                )
            return

        if answer in {"لا", "non", "no"}:
            resume_state = state.get("resume_state")
            if resume_state:
                await set_state(chat_id=chat_id, state=resume_state)
            else:
                await delete_state(chat_id=chat_id)
            await send_message(chat_id=chat_id, text="تم إلغاء العملية.")
            return

        await send_message(
            chat_id=chat_id,
            text="الرجاء الإجابة بنعم أو لا لتأكيد العملية.",
        )
        return

    if state and (
        state.get("flow") == "owner"
        or (state.get("flow") == "customer" and text.isdigit())
    ):
        logger.info(
            "state_dispatch_started",
            extra={
                "chat_id": chat_id,
                "flow": state.get("flow"),
                "step": state.get("step"),
            },
        )
        await StateDispatcher.dispatch(
            chat_id=chat_id,
            text=text,
            state=state,
            message_id=message_id,
        )
        return

    if not text:
        return

    logger.info(
        "agent_message_dispatch_started",
        extra={"chat_id": chat_id},
    )

    result = await agent_engine.process(
        user_id=chat_id,
        message=text,
        session_id=f"telegram_{chat_id}",
        channel="telegram",
        context={
            "chat_id": chat_id,
            "restaurant_id": state.get("restaurant_id") if state else None,
        },
    )
    action_result = result.get("action_result", {})
    if action_result.get("data", {}).get("pending_confirmation"):
        resume_state = None
        if state and state.get("flow") == "customer":
            resume_state = {
                "flow": "customer",
                "step": state.get("step"),
                "restaurant_id": state.get("restaurant_id"),
                "restaurant_name": state.get("restaurant_name"),
                "cart": state.get("cart", []),
                "products": [
                    product if isinstance(product, dict) else {
                        "id": getattr(product, "id", None),
                        "name": getattr(product, "name", None),
                        "price": getattr(product, "price", None),
                    }
                    for product in state.get("products", [])
                ],
            }
        await set_state(
            chat_id=chat_id,
            state={
                "flow": "agent_confirmation",
                "action": action_result.get("action"),
                "params": action_result["data"].get("params", {}),
                "context": action_result["data"].get("context", {}),
                "resume_state": resume_state,
            },
        )
    response = result.get("response")
    if response:
        await send_message(chat_id=chat_id, text=response)
    return