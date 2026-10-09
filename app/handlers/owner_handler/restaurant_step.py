# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / OWNER_HANDLER / RESTAURANT STEP
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for restaurant step.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
    Dict,
)

from app.core.logger import logger

from app.helpers.ui_helpers import send_wilaya_name
from app.helpers.safe_sanitize import safe_sanitize
from app.helpers.state_transition import transition_to
from app.helpers.ui_manager import UIManager
from app.helpers.state_helper import (
    update_state_field,
    get_user_state,
)

from app.states.owner_states import OwnerStates
from app.views.ui import back_ui

# ==============================================
# 🧩 TYPES
# ==============================================

StateData = Dict[str, Any]


# ==============================================
# 🏪 HANDLE RESTAURANT STEP
# ==============================================


async def handle_restaurant_step(
    *,
    chat_id: int,
    text: str,
    state: StateData,
    message_id: int,
) -> None:
    """
    معالجة إدخال اسم المحل والانتقال إلى خطوة الولاية.

    Args:
        chat_id: معرف المستخدم في تيليجرام
        text: النص المدخل من المستخدم
        state: حالة المستخدم الحالية
        message_id: معرف رسالة المستخدم
    """
    logger.info(
        "handle_restaurant_step_started",
        extra={
            "chat_id": chat_id,
            "text_length": len(text),
        },
    )

    # ==========================================
    # 💾 تخزين معرف رسالة المستخدم
    # ==========================================

    await _store_user_message_id(
        chat_id=chat_id,
        message_id=message_id,
    )

    # ==========================================
    # 🧼 SANITIZE INPUT
    # ==========================================

    clean = safe_sanitize(
        chat_id=chat_id,
        text=text,
        field="restaurant",
    )

    if clean is None:
        await _handle_invalid_input(
            chat_id=chat_id,
            state=state,
        )
        return

    # ==========================================
    # 💾 SAVE STATE
    # ==========================================

    await _save_restaurant_name(
        chat_id=chat_id,
        restaurant_name=clean,
    )

    # ==========================================
    # 🔄 TRANSITION TO WILAYA STEP
    # ==========================================

    await _transition_to_wilaya(
        chat_id=chat_id,
        state=state,
        message_id=message_id,
    )


# ==========================================
# 🛠️ PRIVATE HELPERS
# ==========================================


async def _store_user_message_id(
    *,
    chat_id: int,
    message_id: int,
) -> None:
    """
    تخزين معرف رسالة المستخدم في Redis.

    Args:
        chat_id: معرف المستخدم
        message_id: معرف الرسالة
    """
    logger.info(
        "storing_user_message_id",
        extra={
            "chat_id": chat_id,
            "message_id": message_id,
        },
    )

    await update_state_field(
        chat_id=chat_id,
        key="user_message_id_restaurant",
        value=message_id,
    )

    logger.info(
        "user_message_id_stored",
        extra={
            "chat_id": chat_id,
            "message_id": message_id,
        },
    )


# ==============================================
#  HANDLE INVALID INPUT
# ==============================================


async def _handle_invalid_input(
    *,
    chat_id: int,
    state: StateData,
) -> None:
    """
    معالجة الإدخال غير الصحيح.

    Args:
        chat_id: معرف المستخدم
        state: حالة المستخدم الحالية
    """
    logger.warning(
        "invalid_restaurant_name",
        extra={"chat_id": chat_id},
    )

    restaurant_message_id = state.get("restaurant_message_id")

    if restaurant_message_id:
        await UIManager.edit(
            chat_id=chat_id,
            message_id=restaurant_message_id,
            text="❌ اسم المحل غير صالح. يرجى إدخال اسم صحيح.",
            reply_markup=await back_ui(),
        )
    else:
        await UIManager.send_new_message(
            chat_id=chat_id,
            text="❌ اسم المحل غير صالح. يرجى إدخال اسم صحيح.",
            reply_markup=await back_ui(),
        )


# ==============================================
#  SAVE RESTAURANT NAME
# ==============================================


async def _save_restaurant_name(
    *,
    chat_id: int,
    restaurant_name: str,
) -> None:
    """
    حفظ اسم المطعم في Redis.

    Args:
        chat_id: معرف المستخدم
        restaurant_name: اسم المطعم
    """
    await update_state_field(
        chat_id=chat_id,
        key="restaurant",
        value=restaurant_name,
    )

    logger.info(
        "restaurant_name_saved",
        extra={
            "chat_id": chat_id,
            "restaurant_name": restaurant_name,
        },
    )


# ==============================================
#  TRANSITION TO WILAYA
# ==============================================


async def _transition_to_wilaya(
    *,
    chat_id: int,
    state: StateData,
    message_id: int,
) -> None:
    """
    الانتقال إلى خطوة الولاية.

    Args:
        chat_id: معرف المستخدم
        state: حالة المستخدم الحالية
        message_id: معرف رسالة المستخدم
    """
    # ✅ جلب الحالة المحدثة من Redis
    updated_state = await get_user_state(chat_id=chat_id)

    if not await transition_to(
        chat_id=chat_id,
        state=updated_state,
        next_state=OwnerStates.WILAYA,
    ):
        logger.error(
            "restaurant_transition_to_wilaya_failed",
            extra={"chat_id": chat_id},
        )
        return

    # ==========================================
    # 🗺️ إرسال شاشة اختيار الولاية
    # ==========================================

    restaurant_message_id = updated_state.get("restaurant_message_id")

    if not restaurant_message_id:
        logger.warning(
            "restaurant_message_id_not_found_using_user_message_id",
            extra={
                "chat_id": chat_id,
                "message_id": message_id,
            },
        )
        restaurant_message_id = message_id

    wilaya_message_id = await send_wilaya_name(
        chat_id=chat_id,
        message_id=restaurant_message_id,
    )

    if wilaya_message_id:
        await update_state_field(
            chat_id=chat_id,
            key="wilaya_message_id",
            value=wilaya_message_id,
        )

        logger.info(
            "wilaya_message_id_saved",
            extra={
                "chat_id": chat_id,
                "wilaya_message_id": wilaya_message_id,
            },
        )
