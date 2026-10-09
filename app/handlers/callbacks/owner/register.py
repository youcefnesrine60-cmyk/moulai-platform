# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / OWNER / REGISTER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for register.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from app.core.logger import logger
from app.helpers.state_helper import clear_user_state
from app.helpers.ui_manager import UIManager
from app.repositories.state_repo import set_state
from app.repositories.user_repo import give_consent, has_consent
from app.states.owner_states import OwnerStates
from app.handlers.callbacks.customer.restaurant_list import show_restaurants
from app.services.telegram import delete_message
from app.views.texts import OWNER_NAME
from app.views.ui import back_ui, consent_text, consent_ui

# ==============================================
# 👤 OWNER CALLBACK
# ==============================================


async def owner_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    معالجة اختيار "صاحب محل" من القائمة الرئيسية
    """
    logger.info(
        "owner_callback_triggered",
        extra={
            "chat_id": chat_id,
            "message_id": message_id,
        },
    )

    # ==========================================
    # 🚫 CONSENT REQUIRED
    # ==========================================

    if not await has_consent(chat_id=chat_id):
        logger.info(
            "owner_consent_required",
            extra={
                "chat_id": chat_id,
            },
        )

        # ✅ حذف القائمة الرئيسية
        await delete_message(
            chat_id=chat_id,
            message_id=message_id,
        )

        # ✅ تنظيف الرسائل المخزنة
        await UIManager.cleanup_messages(chat_id=chat_id)

        # ✅ إرسال رسالة الموافقة
        await UIManager.send_new_message(
            chat_id=chat_id,
            text=await consent_text(),
            reply_markup=await consent_ui(role="owner"),
            store_message_id=True,
        )
        return

    # ==========================================
    # 🧹 CLEANUP PREVIOUS STATE
    # ==========================================

    await clear_user_state(chat_id=chat_id)

    # ✅ حذف القائمة الرئيسية فقط
    await delete_message(
        chat_id=chat_id,
        message_id=message_id,
    )

    # ✅ تنظيف الرسائل المخزنة (بدون حذف القائمة الرئيسية لأنها محذوفة بالفعل)
    await UIManager.cleanup_messages(chat_id=chat_id)

    # ==========================================
    # 🚀 START OWNER FLOW
    # ==========================================

    # ✅ إنشاء حالة جديدة مع bot_message_id = None
    # لأننا سنرسل رسالة جديدة ولا نعدل رسالة موجودة
    await set_state(
        chat_id=chat_id,
        state={
            "flow": "owner",
            "step": OwnerStates.NAME,
            "history": [],
            "bot_message_id": None,  # ← مهم: لا يوجد رسالة بوت سابقة
        },
    )

    logger.info(
        "owner_flow_started",
        extra={
            "chat_id": chat_id,
        },
    )

    # ✅ إرسال رسالة جديدة لإدخال الاسم
    response = await UIManager.send_new_message(
        chat_id=chat_id,
        text=OWNER_NAME,
        reply_markup=await back_ui(),
        store_message_id=True,
    )

    # ✅ تحديث bot_message_id بالرسالة الجديدة
    if response and isinstance(response, dict):
        new_message_id = response.get("result", {}).get("message_id")
        if new_message_id:
            from app.helpers.state_helper import update_state_field

            await update_state_field(
                chat_id=chat_id,
                key="bot_message_id",
                value=new_message_id,
            )
            logger.info(
                "bot_message_id_updated",
                extra={
                    "chat_id": chat_id,
                    "bot_message_id": new_message_id,
                },
            )


# ==============================================
# ✅ CONSENT CALLBACK
# ==============================================


async def consent_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    معالجة الموافقة على الشروط بطريقة محسنة
    """
    # تسجيل الموافقة
    await give_consent(chat_id=chat_id)

    # تنظيف الرسائل المخزنة
    await UIManager.cleanup_messages(
        chat_id=chat_id,
        preserve_message_id=message_id,
    )

    if callback_data.endswith("owner"):
        logger.info(
            "owner_consent_accepted",
            extra={
                "chat_id": chat_id,
            },
        )

        # تنظيف الحالة السابقة
        await clear_user_state(chat_id=chat_id)

        # ✅ حذف رسالة الموافقة
        await delete_message(
            chat_id=chat_id,
            message_id=message_id,
        )

        # ✅ إرسال رسالة جديدة لإدخال الاسم
        response = await UIManager.send_new_message(
            chat_id=chat_id,
            text=OWNER_NAME,
            reply_markup=await back_ui(),
            store_message_id=True,
        )

        # ✅ تحديث bot_message_id
        if response and isinstance(response, dict):
            new_message_id = response.get("result", {}).get("message_id")
            if new_message_id:
                from app.helpers.state_helper import update_state_field

                await update_state_field(
                    chat_id=chat_id,
                    key="bot_message_id",
                    value=new_message_id,
                )

        return

    # ==========================================
    # 👤 CUSTOMER CONSENT
    # ==========================================

    logger.info(
        "customer_consent_accepted",
        extra={
            "chat_id": chat_id,
        },
    )

    await show_restaurants(
        chat_id=chat_id,
        message_id=message_id,
    )
