# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / OWNER_HANDLER / WILAYA STEP
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for wilaya step.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import Any

from app.core.logger import logger
from app.helpers.safe_sanitize import safe_sanitize
from app.helpers.state_helper import (
    update_state_field,
    get_user_state,
)
from app.helpers.state_transition import transition_to
from app.helpers.ui_manager import UIManager
from app.states.owner_states import OwnerStates
from app.views.ui import back_ui, location_webapp_ui

# ==============================================
# 🧩 TYPES
# ==============================================

StateData = dict[str, Any]


# ==============================================
# 🗺️ HANDLE WILAYA STEP
# ==============================================


async def handle_wilaya_step(
    *,
    chat_id: int,
    text: str,
    state: StateData,
    message_id: int,
) -> None:
    """
    معالجة إدخال اسم الولاية

    Args:
        chat_id: معرف المستخدم
        text: النص المدخل
        state: حالة المستخدم الحالية
        message_id: معرف رسالة المستخدم (تبقى ظاهرة)
    """
    logger.info(
        "handle_wilaya_step",
        extra={
            "chat_id": chat_id,
            "text_length": len(text),
        },
    )

    # ==========================================
    # 💾 تخزين معرف رسالة المستخدم (لحذفها عند الرجوع)
    # ==========================================

    logger.info(
        "before_storing_user_message_id_wilaya",
        extra={
            "chat_id": chat_id,
            "message_id": message_id,
        },
    )

    # يخزن user_message_id_wilaya في Redis
    await update_state_field(
        chat_id=chat_id,
        key="user_message_id_wilaya",
        value=message_id,
    )

    logger.info(
        "after_storing_user_message_id_wilaya",
        extra={
            "chat_id": chat_id,
            "message_id": message_id,
        },
    )

    # ==========================================
    # 🔍 التحقق من التخزين في Redis
    # ==========================================

    state_after = await get_user_state(chat_id=chat_id)
    logger.info(
        "verify_user_message_id_wilaya_stored",
        extra={
            "chat_id": chat_id,
            "user_message_id_wilaya": (
                state_after.get("user_message_id_wilaya") if state_after else None
            ),
            "wilaya_message_id": (
                state_after.get("wilaya_message_id") if state_after else None
            ),
            "step": state_after.get("step") if state_after else None,
            "all_keys": list(state_after.keys()) if state_after else [],
        },
    )

    # ==========================================
    # 🧼 SANITIZE INPUT
    # ==========================================

    clean = safe_sanitize(
        chat_id=chat_id,
        text=text,
        field="wilaya",
    )

    # ==========================================
    # 🚫 INVALID INPUT
    # ==========================================

    if clean is None:
        logger.warning(
            "invalid_wilaya_name",
            extra={
                "chat_id": chat_id,
            },
        )

        wilaya_message_id = state.get("wilaya_message_id")

        if wilaya_message_id:
            await UIManager.edit(
                chat_id=chat_id,
                message_id=wilaya_message_id,
                text="❌ اسم الولاية غير صالح. يرجى إدخال اسم صحيح.",
                reply_markup=await back_ui(),
            )
        else:
            await UIManager.send_new_message(
                chat_id=chat_id,
                text="❌ اسم الولاية غير صالح. يرجى إدخال اسم صحيح.",
                reply_markup=await back_ui(),
            )
        return

    # ==========================================
    # 💾 SAVE STATE
    # ==========================================

    # ✅ تخزين اسم الولاية فقط (بدون تحديث step)
    await update_state_field(
        chat_id=chat_id,
        key="wilaya",
        value=clean,
    )

    logger.info(
        "wilaya_name_saved",
        extra={
            "chat_id": chat_id,
            "wilaya_name": clean,
        },
    )

    # ==========================================
    # 🔄 TRANSITION TO LOCATION STEP
    # ==========================================

    # ✅ جلب الحالة المحدثة من Redis
    state = await get_user_state(chat_id=chat_id)

    if not await transition_to(
        chat_id=chat_id,
        state=state,
        next_state=OwnerStates.LOCATION,
    ):
        logger.error(
            "wilaya_transition_to_location_failed",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    # ==========================================
    # 📍 SEND LOCATION SCREEN
    # ==========================================

    wilaya_message_id = state.get("wilaya_message_id")

    if not wilaya_message_id:
        logger.warning(
            "wilaya_message_id_not_found_using_user_message_id",
            extra={
                "chat_id": chat_id,
                "message_id": message_id,
            },
        )
        wilaya_message_id = message_id

    # ✅ تحديث رسالة البوت لإظهار "تم حفظ الولاية"
    await UIManager.edit(
        chat_id=chat_id,
        message_id=wilaya_message_id,
        text=f"🗺️ ✅ تم حفظ الولاية: {clean}",
        reply_markup=None,
    )

    # ✅ إرسال رسالة جديدة لخطوة الموقع
    response = await UIManager.send_new_message(
        chat_id=chat_id,
        text="📍 اضغط على الزر لتحديد موقع المحل على الخريطة:",
        reply_markup=await location_webapp_ui(),
        store_message_id=True,
    )

    # ✅ حفظ معرف رسالة الموقع
    if response and isinstance(response, dict):
        location_message_id = response.get("result", {}).get("message_id")
        if location_message_id:
            await update_state_field(
                chat_id=chat_id,
                key="location_message_id",
                value=location_message_id,
            )

            logger.info(
                "location_message_id_saved",
                extra={
                    "chat_id": chat_id,
                    "location_message_id": location_message_id,
                },
            )
