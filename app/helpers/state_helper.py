# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HELPERS / STATE HELPER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for state helper.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import Any
from datetime import datetime, timezone

from app.core.logger import logger
from app.repositories.state_repo import (
    delete_state,
    get_state,
    set_state,
)

# ==============================================
# 🧩 TYPES
# ==============================================

StateData = dict[str, Any]


# ==============================================
# 📥 GET STATE
# ==============================================


async def get_user_state(
    *,
    chat_id: int,
) -> StateData | None:
    """
    جلب حالة المستخدم

    Args:
        chat_id: معرف المستخدم

    Returns:
        StateData | None: بيانات الحالة أو None إذا لم توجد
    """
    try:
        state = await get_state(chat_id=chat_id)

        logger.debug(
            "user_state_retrieved",
            extra={
                "chat_id": chat_id,
                "exists": state is not None,
            },
        )

        return state

    except Exception as e:
        logger.error(
            "get_user_state_failed",
            extra={
                "chat_id": chat_id,
                "error": str(e),
            },
        )
        return None


# ==============================================
# 💾 UPDATE STATE FIELD
# ==============================================


async def update_state_field(
    *,
    chat_id: int,
    key: str,
    value: Any,
) -> bool:
    """
    تحديث حقل معين في الحالة دون فقدان البيانات الأخرى

    Args:
        chat_id: معرف المستخدم
        key: اسم الحقل المراد تحديثه
        value: القيمة الجديدة

    Returns:
        bool: True إذا تم التحديث بنجاح
    """
    try:
        state = await get_state(chat_id=chat_id)

        if state is None:
            state = {}

        state[key] = value

        await set_state(chat_id=chat_id, state=state)

        logger.debug(
            "state_field_updated",
            extra={
                "chat_id": chat_id,
                "key": key,
                "value_type": type(value).__name__,
            },
        )

        return True

    except Exception as e:
        logger.error(
            "state_field_update_failed",
            extra={
                "chat_id": chat_id,
                "key": key,
                "error": str(e),
            },
        )
        return False


# ==============================================
# 📥 APPEND TO STATE LIST
# ==============================================


async def append_to_state_list(
    *,
    chat_id: int,
    list_key: str,
    value: Any,
    unique: bool = True,
) -> bool:
    """
    إضافة عنصر إلى قائمة في الحالة

    Args:
        chat_id: معرف المستخدم
        list_key: مفتاح القائمة في الحالة
        value: القيمة المراد إضافتها
        unique: منع التكرار (افتراضي True)

    Returns:
        bool: True إذا تمت الإضافة بنجاح
    """
    try:
        state = await get_state(chat_id=chat_id)

        if state is None:
            state = {}

        # التأكد من وجود القائمة
        if list_key not in state or not isinstance(state[list_key], list):
            state[list_key] = []

        # منع التكرار إذا كان مطلوباً
        if unique and value in state[list_key]:
            logger.debug(
                "value_already_in_list",
                extra={
                    "chat_id": chat_id,
                    "list_key": list_key,
                    "value": value,
                },
            )
            return True

        # إضافة القيمة
        state[list_key].append(value)

        # حفظ الحالة
        await set_state(chat_id=chat_id, state=state)

        logger.debug(
            "state_list_appended",
            extra={
                "chat_id": chat_id,
                "list_key": list_key,
                "value": value,
                "list_length": len(state[list_key]),
            },
        )

        return True

    except Exception as e:
        logger.error(
            "state_list_append_failed",
            extra={
                "chat_id": chat_id,
                "list_key": list_key,
                "error": str(e),
            },
        )
        return False


# ==============================================
# 📤 REMOVE FROM STATE LIST
# ==============================================


async def remove_from_state_list(
    *,
    chat_id: int,
    list_key: str,
    value: Any,
) -> bool:
    """
    إزالة عنصر من قائمة في الحالة

    Args:
        chat_id: معرف المستخدم
        list_key: مفتاح القائمة في الحالة
        value: القيمة المراد إزالتها

    Returns:
        bool: True إذا تمت الإزالة بنجاح
    """
    try:
        state = await get_state(chat_id=chat_id)

        if state is None:
            return True

        if list_key not in state or not isinstance(state[list_key], list):
            return True

        # إزالة القيمة إذا كانت موجودة
        if value in state[list_key]:
            state[list_key].remove(value)

            # حفظ الحالة
            await set_state(chat_id=chat_id, state=state)

            logger.debug(
                "state_list_item_removed",
                extra={
                    "chat_id": chat_id,
                    "list_key": list_key,
                    "value": value,
                    "list_length": len(state[list_key]),
                },
            )

        return True

    except Exception as e:
        logger.error(
            "state_list_remove_failed",
            extra={
                "chat_id": chat_id,
                "list_key": list_key,
                "error": str(e),
            },
        )
        return False


# ==============================================
# 🧹 CLEAR USER STATE
# ==============================================


async def clear_user_state(
    *,
    chat_id: int,
) -> bool:
    """
    حذف حالة المستخدم بالكامل بشكل آمن

    Args:
        chat_id: معرف المستخدم

    Returns:
        bool: True إذا تم الحذف بنجاح
    """
    try:
        await delete_state(chat_id=chat_id)

        logger.info(
            "user_state_cleared",
            extra={
                "chat_id": chat_id,
            },
        )
        return True

    except Exception as e:
        logger.error(
            "clear_user_state_failed",
            extra={
                "chat_id": chat_id,
                "error": str(e),
            },
        )
        return False


# ==============================================
# 🔄 INITIALIZE USER STATE
# ==============================================


async def initialize_user_state(
    *,
    chat_id: int,
    initial_data: StateData | None = None,
) -> bool:
    """
    تهيئة حالة جديدة للمستخدم

    Args:
        chat_id: معرف المستخدم
        initial_data: البيانات الأولية (اختياري)

    Returns:
        bool: True إذا تمت التهيئة بنجاح
    """
    try:
        # التأكد من عدم وجود حالة سابقة
        existing_state = await get_state(chat_id=chat_id)

        if existing_state is not None:
            logger.warning(
                "user_state_already_exists",
                extra={
                    "chat_id": chat_id,
                },
            )
            return True

        # إنشاء حالة جديدة
        state = initial_data or {}

        # إضافة حقول افتراضية
        if "message_ids" not in state:
            state["message_ids"] = []

        if "created_at" not in state:
            state["created_at"] = datetime.now(timezone.utc).isoformat()

        await set_state(chat_id=chat_id, state=state)

        logger.info(
            "user_state_initialized",
            extra={
                "chat_id": chat_id,
                "fields": list(state.keys()),
            },
        )
        return True

    except Exception as e:
        logger.error(
            "initialize_user_state_failed",
            extra={
                "chat_id": chat_id,
                "error": str(e),
            },
        )
        return False


# ==============================================
# 🔍 GET STATE FIELD
# ==============================================


async def get_state_field(
    *,
    chat_id: int,
    key: str,
    default: Any = None,
) -> Any:
    """
    جلب قيمة حقل معين من الحالة

    Args:
        chat_id: معرف المستخدم
        key: اسم الحقل
        default: القيمة الافتراضية إذا لم يوجد الحقل

    Returns:
        Any: قيمة الحقل أو القيمة الافتراضية
    """
    try:
        state = await get_state(chat_id=chat_id)

        if state is None:
            return default

        return state.get(key, default)

    except Exception as e:
        logger.error(
            "get_state_field_failed",
            extra={
                "chat_id": chat_id,
                "key": key,
                "error": str(e),
            },
        )
        return default


# ==============================================
# 📊 UPDATE MULTIPLE STATE FIELDS
# ==============================================


async def update_state_fields(
    *,
    chat_id: int,
    fields: dict[str, Any],
) -> bool:
    """
    تحديث عدة حقول في الحالة دفعة واحدة

    Args:
        chat_id: معرف المستخدم
        fields: قاموس الحقول والقيم الجديدة

    Returns:
        bool: True إذا تم التحديث بنجاح
    """
    try:
        if not fields:
            return True

        state = await get_state(chat_id=chat_id)

        if state is None:
            state = {}

        # تحديث جميع الحقول
        state.update(fields)

        await set_state(chat_id=chat_id, state=state)

        logger.debug(
            "state_fields_updated",
            extra={
                "chat_id": chat_id,
                "fields_count": len(fields),
                "fields": list(fields.keys()),
            },
        )

        return True

    except Exception as e:
        logger.error(
            "state_fields_update_failed",
            extra={
                "chat_id": chat_id,
                "error": str(e),
            },
        )
        return False
