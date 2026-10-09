# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / OWNER / NAVIGATION
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for navigation.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from app.core.logger import logger

from app.helpers.navigation import go_back
from app.helpers.state_helper import (
    clear_user_state,
    get_user_state,
    update_state_field,
)
from app.helpers.ui_manager import UIManager

from app.services.telegram import delete_message

from app.states.owner_states import OwnerStates

from app.views.texts import (
    OWNER_NAME,
    PHONE_NUMBER,
    RESTAU_NAME,
    WELCOME_MESSAGE,
    WILAYA_NAME,
)
from app.views.ui import (
    back_ui,
    location_webapp_ui,
    main_menu_ui,
    types_ui,
)

# ==============================================
# 🧩 TYPES
# ==============================================

ReplyMarkup = dict[str, object] | None


# ==============================================
# 🧹 DELETE STEP MESSAGES
# ==============================================


async def _delete_step_messages(
    *,
    chat_id: int,
    step: str,
    state: dict,
) -> int:
    """
    حذف رسائل خطوة معينة (رسالة المستخدم + رسالة البوت)

    ملاحظة: رسالة المستخدم تحذف فقط إذا كانت موجودة (أي إذا كان المستخدم قد أرسلها بالفعل)

    Args:
        chat_id: معرف المحادثة
        step: اسم الخطوة
        state: حالة المستخدم

    Returns:
        int: عدد الرسائل المحذوفة
    """
    deleted_count = 0

    # ==========================================
    # 📝 تحديد معرفات الرسائل حسب الخطوة
    # ==========================================

    user_message_key = None
    bot_message_key = None

    if step == OwnerStates.NAME:
        user_message_key = "user_message_id_name"
        bot_message_key = "bot_message_id"
    elif step == OwnerStates.RESTAURANT:
        user_message_key = "user_message_id_restaurant"
        bot_message_key = "restaurant_message_id"
    elif step == OwnerStates.WILAYA:
        user_message_key = "user_message_id_wilaya"
        bot_message_key = "wilaya_message_id"
    elif step == OwnerStates.PHONE:
        user_message_key = "user_message_id_phone"
        bot_message_key = "phone_message_id"
    elif step == OwnerStates.LOCATION:
        user_message_key = "user_message_id_location"
        bot_message_key = "location_message_id"
    elif step == OwnerStates.TYPE:
        user_message_key = "user_message_id_type"
        bot_message_key = "type_message_id"

    # ==========================================
    # 🗑️ حذف رسالة المستخدم (إذا كانت موجودة)
    # ==========================================

    if user_message_key:
        user_message_id = state.get(user_message_key)
        if user_message_id:
            try:
                await delete_message(
                    chat_id=chat_id,
                    message_id=user_message_id,
                )
                deleted_count += 1
                logger.debug(
                    "user_message_deleted_for_step",
                    extra={
                        "chat_id": chat_id,
                        "step": step,
                        "message_id": user_message_id,
                    },
                )
            except Exception as e:
                logger.warning(
                    "user_message_delete_failed",
                    extra={
                        "chat_id": chat_id,
                        "step": step,
                        "message_id": user_message_id,
                        "error": str(e),
                    },
                )

    # ==========================================
    # 🗑️ حذف رسالة البوت
    # ==========================================

    if bot_message_key:
        bot_message_id = state.get(bot_message_key)
        if bot_message_id:
            try:
                await delete_message(
                    chat_id=chat_id,
                    message_id=bot_message_id,
                )
                deleted_count += 1
                logger.debug(
                    "bot_message_deleted_for_step",
                    extra={
                        "chat_id": chat_id,
                        "step": step,
                        "message_id": bot_message_id,
                    },
                )
            except Exception as e:
                logger.warning(
                    "bot_message_delete_failed",
                    extra={
                        "chat_id": chat_id,
                        "step": step,
                        "message_id": bot_message_id,
                        "error": str(e),
                    },
                )

    return deleted_count


# ==============================================
# 🧹 CLEANUP STEP MESSAGES FROM STATE
# ==============================================


async def _cleanup_step_from_state(
    *,
    chat_id: int,
    step: str,
) -> None:
    """
    إزالة معرفات رسائل خطوة معينة من الحالة

    Args:
        chat_id: معرف المحادثة
        step: اسم الخطوة
    """
    user_message_key = None
    bot_message_key = None

    if step == OwnerStates.NAME:
        user_message_key = "user_message_id_name"
        bot_message_key = "bot_message_id"
    elif step == OwnerStates.RESTAURANT:
        user_message_key = "user_message_id_restaurant"
        bot_message_key = "restaurant_message_id"
    elif step == OwnerStates.WILAYA:
        user_message_key = "user_message_id_wilaya"
        bot_message_key = "wilaya_message_id"
    elif step == OwnerStates.PHONE:
        user_message_key = "user_message_id_phone"
        bot_message_key = "phone_message_id"
    elif step == OwnerStates.LOCATION:
        user_message_key = "user_message_id_location"
        bot_message_key = "location_message_id"
    elif step == OwnerStates.TYPE:
        user_message_key = "user_message_id_type"
        bot_message_key = "type_message_id"

    if user_message_key:
        await update_state_field(
            chat_id=chat_id,
            key=user_message_key,
            value=None,
        )

    if bot_message_key:
        await update_state_field(
            chat_id=chat_id,
            key=bot_message_key,
            value=None,
        )


# ==============================================
# 🔙 BACK STEP CALLBACK
# ==============================================


async def back_step_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match,
) -> None:
    """
    العودة إلى الخطوة السابقة مع حذف رسائل الخطوتين

    المنطق:
    - الخطوة الحالية: يوجد فقط رسالة البوت (تحذف)
    - الخطوة السابقة: يوجد رسالة المستخدم + رسالة البوت (تحذف كلتاهما)
    """
    try:
        # ==========================================
        # 📥 جلب الحالة
        # ==========================================

        logger.info(
            "back_step_state_before_get",
            extra={
                "chat_id": chat_id,
            },
        )

        state = await get_user_state(chat_id=chat_id)

        logger.info(
            "back_step_initial_state",
            extra={
                "chat_id": chat_id,
                "user_message_id_restaurant": (
                    state.get("user_message_id_restaurant") if state else None
                ),
                "restaurant_message_id": (
                    state.get("restaurant_message_id") if state else None
                ),
                "step": state.get("step") if state else None,
                "all_keys": list(state.keys()) if state else [],
            },
        )

        if not state:
            logger.warning(
                "state_not_found_on_back",
                extra={
                    "chat_id": chat_id,
                },
            )
            await back_to_main_menu(chat_id=chat_id)
            return

        # ==========================================
        # 📍 تحديد الخطوة الحالية
        # ==========================================

        current_step = state.get("step")

        if not current_step:
            logger.warning(
                "current_step_not_found",
                extra={
                    "chat_id": chat_id,
                },
            )
            await back_to_main_menu(chat_id=chat_id)
            return

        logger.info(
            "back_step_started",
            extra={
                "chat_id": chat_id,
                "current_step": current_step,
            },
        )

        # ==========================================
        # 🔙 العودة إلى الخطوة السابقة
        # ==========================================

        previous_step = await go_back(chat_id=chat_id)

        # ==========================================
        # 🏠 لا توجد خطوة سابقة → القائمة الرئيسية
        # ==========================================

        if not previous_step:
            logger.info(
                "back_button_no_previous_step",
                extra={
                    "chat_id": chat_id,
                    "current_step": current_step,
                },
            )

            # حذف جميع الرسائل
            await UIManager.cleanup_messages(chat_id=chat_id)
            await clear_user_state(chat_id=chat_id)

            # عرض القائمة الرئيسية
            await UIManager.send_new_message(
                chat_id=chat_id,
                text=WELCOME_MESSAGE,
                reply_markup=await main_menu_ui(),
            )
            return

        # ==========================================
        # 🧹 حذف رسائل الخطوة الحالية (البوت فقط)
        # ==========================================

        deleted_current = await _delete_step_messages(
            chat_id=chat_id,
            step=current_step,
            state=state,
        )

        logger.info(
            "state_before_cleanup",
            extra={
                "chat_id": chat_id,
                "user_message_id_restaurant": state.get("user_message_id_restaurant"),
                "restaurant_message_id": state.get("restaurant_message_id"),
            },
        )

        await _cleanup_step_from_state(
            chat_id=chat_id,
            step=current_step,
        )

        logger.info(
            "current_step_messages_deleted",
            extra={
                "chat_id": chat_id,
                "step": current_step,
                "deleted_count": deleted_current,
            },
        )

        # ==========================================
        # 🧹 حذف رسائل الخطوة السابقة (المستخدم + البوت)
        # ==========================================

        # ✅ جلب الحالة مرة أخرى
        state = await get_user_state(chat_id=chat_id)

        logger.info(
            "state_content_before_delete",
            extra={
                "chat_id": chat_id,
                "step": previous_step,
                "user_message_id_restaurant": state.get("user_message_id_restaurant"),
                "restaurant_message_id": state.get("restaurant_message_id"),
            },
        )

        deleted_previous = await _delete_step_messages(
            chat_id=chat_id,
            step=previous_step,
            state=state,
        )

        await _cleanup_step_from_state(
            chat_id=chat_id,
            step=previous_step,
        )

        logger.info(
            "previous_step_messages_deleted",
            extra={
                "chat_id": chat_id,
                "step": previous_step,
                "deleted_count": deleted_previous,
            },
        )

        # ==========================================
        # 📝 تحديث الحالة للخطوة الجديدة
        # ==========================================

        await update_state_field(
            chat_id=chat_id,
            key="step",
            value=previous_step,
        )

        # ==========================================
        # 📝 TEXT STEPS MAPPING
        # ==========================================

        STEPS_TEXT = {
            OwnerStates.NAME: OWNER_NAME,
            OwnerStates.RESTAURANT: RESTAU_NAME,
            OwnerStates.WILAYA: WILAYA_NAME,
            OwnerStates.PHONE: PHONE_NUMBER,
        }

        # ==========================================
        # 📍 LOCATION STEP
        # ==========================================

        if previous_step == OwnerStates.LOCATION:
            logger.info(
                "back_to_location_step",
                extra={
                    "chat_id": chat_id,
                    "step": previous_step,
                },
            )

            response = await UIManager.send_new_message(
                chat_id=chat_id,
                text="📍 اضغط على الزر لفتح الخريطة واختيار موقع المحل:",
                reply_markup=await location_webapp_ui(),
                store_message_id=True,
            )

            if response and isinstance(response, dict):
                new_message_id = response.get("result", {}).get("message_id")
                if new_message_id:
                    await update_state_field(
                        chat_id=chat_id,
                        key="location_message_id",
                        value=new_message_id,
                    )

        # ==========================================
        # 🍽️ TYPE STEP
        # ==========================================

        elif previous_step == OwnerStates.TYPE:
            logger.info(
                "back_to_type_step",
                extra={
                    "chat_id": chat_id,
                    "step": previous_step,
                },
            )

            response = await UIManager.send_new_message(
                chat_id=chat_id,
                text="🍽️ اختر نوع المحل:",
                reply_markup=await types_ui(),
                store_message_id=True,
            )

            if response and isinstance(response, dict):
                new_message_id = response.get("result", {}).get("message_id")
                if new_message_id:
                    await update_state_field(
                        chat_id=chat_id,
                        key="type_message_id",
                        value=new_message_id,
                    )

        # ==========================================
        # 📝 TEXT INPUT STEP
        # ==========================================

        elif previous_step in STEPS_TEXT:
            logger.info(
                "back_to_text_step",
                extra={
                    "chat_id": chat_id,
                    "step": previous_step,
                },
            )

            response = await UIManager.send_new_message(
                chat_id=chat_id,
                text=STEPS_TEXT[previous_step],
                reply_markup=await back_ui(),
                store_message_id=True,
            )

            if response and isinstance(response, dict):
                new_message_id = response.get("result", {}).get("message_id")
                if new_message_id:
                    bot_message_key = None
                    if previous_step == OwnerStates.NAME:
                        bot_message_key = "bot_message_id"
                    elif previous_step == OwnerStates.RESTAURANT:
                        bot_message_key = "restaurant_message_id"
                    elif previous_step == OwnerStates.WILAYA:
                        bot_message_key = "wilaya_message_id"
                    elif previous_step == OwnerStates.PHONE:
                        bot_message_key = "phone_message_id"

                    if bot_message_key:
                        await update_state_field(
                            chat_id=chat_id,
                            key=bot_message_key,
                            value=new_message_id,
                        )

        # ==========================================
        # 🚫 UNKNOWN STEP
        # ==========================================

        else:
            logger.warning(
                "unknown_step_on_back",
                extra={
                    "chat_id": chat_id,
                    "step": previous_step,
                },
            )

            await UIManager.delete(
                chat_id=chat_id,
                message_id=message_id,
            )

            await back_to_main_menu(
                chat_id=chat_id,
                current_message_id=None,
                show_welcome=True,
            )

        logger.info(
            "back_step_completed",
            extra={
                "chat_id": chat_id,
                "from_step": current_step,
                "to_step": previous_step,
            },
        )

    except Exception as e:
        logger.exception(
            "back_step_callback_failed",
            extra={
                "chat_id": chat_id,
                "message_id": message_id,
                "error": str(e),
            },
        )

        try:
            await back_to_main_menu(
                chat_id=chat_id,
                current_message_id=message_id,
                show_welcome=True,
            )
        except Exception as fallback_error:
            logger.error(
                "back_step_fallback_failed",
                extra={
                    "chat_id": chat_id,
                    "error": str(fallback_error),
                },
            )


# ==============================================
# 🔙 BACK TO MAIN MENU
# ==============================================


async def back_to_main_menu(
    *,
    chat_id: int,
    current_message_id: int | None = None,
    show_welcome: bool = True,
) -> bool:
    """
    العودة إلى القائمة الرئيسية مع تنظيف شامل
    """
    try:
        await UIManager.cleanup_messages(chat_id=chat_id)
        await clear_user_state(chat_id=chat_id)

        logger.info(
            "back_to_main_menu",
            extra={
                "chat_id": chat_id,
            },
        )

        text = WELCOME_MESSAGE if show_welcome else "🏠 القائمة الرئيسية"

        await UIManager.send_new_message(
            chat_id=chat_id,
            text=text,
            reply_markup=await main_menu_ui(),
        )

        return True

    except Exception as e:
        logger.exception(
            "back_to_main_menu_failed",
            extra={
                "chat_id": chat_id,
                "error": str(e),
            },
        )
        return False


# ==============================================
# 🔙 BACK MAIN CALLBACK
# ==============================================


async def back_main_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match,
) -> None:
    """
    نقطة الدخول للعودة إلى القائمة الرئيسية
    """
    await back_to_main_menu(
        chat_id=chat_id,
        current_message_id=message_id,
        show_welcome=True,
    )


# ==============================================
# ❌ DECLINE CALLBACK
# ==============================================


async def decline_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match,
) -> None:
    """
    رفض الموافقة على الشروط
    """
    try:
        logger.info(
            "owner_declined_consent",
            extra={
                "chat_id": chat_id,
            },
        )

        await UIManager.cleanup_messages(
            chat_id=chat_id,
            preserve_message_id=message_id,
        )

        await UIManager.edit(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ نعتذر! لا يمكن استخدام البوت بدون الموافقة على سياسة حماية المعطيات",
            reply_markup=await main_menu_ui(),
        )

        await clear_user_state(chat_id=chat_id)

    except Exception as e:
        logger.exception(
            "decline_callback_failed",
            extra={
                "chat_id": chat_id,
                "error": str(e),
            },
        )
