# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / OWNER / CONFIRM
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for confirm.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from app.core.logger import logger

from app.core.middleware.idempotency import Idempotency
from app.core.middleware.rate_limit import rate_limit
from app.helpers.ui_manager import UIManager
from app.services.business.registration_request_service import approve_registration

# ==============================================
# ✅ CONFIRM CALLBACK
# ==============================================


@rate_limit(
    limit=2,
    window=15,
    key_prefix="confirm",
)
async def confirm_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:

    # ==========================================
    # 🛡️ IDEMPOTENCY PROTECTION
    # ==========================================

    allowed = await Idempotency.protect(
        key=f"confirm:{chat_id}",
        ttl=20,
    )

    if not allowed:

        logger.warning(
            "duplicate_confirm_request",
            extra={
                "chat_id": chat_id,
            },
        )

        return

    try:

        # ======================================
        # ✅ APPROVE REGISTRATION
        # ======================================

        result = await approve_registration(
            chat_id=chat_id,
        )

        logger.info(
            "registration_confirmed",
            extra={
                "chat_id": chat_id,
                "owner_id": result["owner_id"],
                "restaurant_id": result["restaurant_id"],
                "subscription_id": result["subscription_id"],
            },
        )

        # ======================================
        # ✅ SUCCESS MESSAGE
        # ======================================

        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                "🎉 تم تسجيل المحل بنجاح.\n\n"
                "✅ تم إنشاء حساب المالك.\n"
                "✅ تم إنشاء المطعم.\n"
                "✅ تم إنشاء إحصائيات المطعم.\n"
                "✅ تم تفعيل الاشتراك التجريبي.\n\n"
                "📦 يمكنك الآن البدء بإضافة الأقسام والمنتجات."
            ),
        )

    except ValueError as error:

        logger.warning(
            "registration_confirm_validation_error",
            extra={
                "chat_id": chat_id,
                "error": str(error),
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ تعذر إكمال عملية التسجيل.",
        )

    except Exception as error:

        logger.exception(
            "confirm_callback_failed",
            extra={
                "chat_id": chat_id,
                "error": str(error),
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ حدث خطأ أثناء معالجة الطلب.",
        )
