# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / PAYMENT / PAYMENT HANDLERS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for payment handlers.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from app.core.logger import logger
from app.core.middleware.rate_limit import rate_limit

from app.helpers.ui_manager import UIManager
from app.repositories.state_repo import get_state, set_state

from app.views.payment_ui import (
    payment_success_ui,
    payment_failed_ui,
)

from app.services.business.order_payments_service import (
    confirm_payment as confirm_order_payment,
    fail_payment as fail_order_payment,
)

# ==============================================
# ✅ PAYMENT SUCCESS (Telegram)
# ==============================================


@rate_limit(
    limit=5,
    window=30,
    key_prefix="payment_success",
)
async def handle_payment_success(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    معالجة نجاح الدفع من داخل Telegram
    """
    try:
        order_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "payment_success_invalid_order_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    logger.info(
        "payment_success_callback",
        extra={
            "chat_id": chat_id,
            "order_id": order_id,
        },
    )

    state = await get_state(chat_id=chat_id)

    if not state:
        logger.warning(
            "state_not_found_payment_success",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    payment_method = state.get("payment_method", "cash")
    amount = state.get("total_amount", 0)

    try:
        await confirm_order_payment(
            payment_id=state.get("payment_id", 0),
        )

        logger.info(
            "order_payment_confirmed",
            extra={
                "chat_id": chat_id,
                "order_id": order_id,
            },
        )

    except ValueError as e:
        logger.warning(
            "order_payment_confirm_failed",
            extra={
                "chat_id": chat_id,
                "order_id": order_id,
                "error": str(e),
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text=f"❌ فشل تأكيد الدفع: {str(e)}",
            reply_markup=await payment_failed_ui(
                order_id=order_id,
                reason=str(e),
            ),
        )
        return

    except Exception as e:
        logger.exception(
            "order_payment_confirm_exception",
            extra={
                "chat_id": chat_id,
                "order_id": order_id,
                "error": str(e),
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ حدث خطأ أثناء تأكيد الدفع.",
            reply_markup=await payment_failed_ui(
                order_id=order_id,
                reason="internal_error",
            ),
        )
        return

    state["payment_status"] = "paid"
    await set_state(chat_id=chat_id, state=state)

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=(
            f"✅ تم الدفع بنجاح!\n\n"
            f"💰 المبلغ: {amount:.2f} دج\n"
            f"💳 طريقة الدفع: {payment_method}\n\n"
            f"📦 سيتم إشعارك عند تجهيز طلبك."
        ),
        reply_markup=await payment_success_ui(
            order_id=order_id,
            payment_method=payment_method,
            amount=amount,
        ),
    )


# ==============================================
# ❌ PAYMENT FAILURE (Telegram)
# ==============================================


@rate_limit(
    limit=5,
    window=30,
    key_prefix="payment_failure",
)
async def handle_payment_failure(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    معالجة فشل الدفع من داخل Telegram
    """
    try:
        order_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "payment_failure_invalid_order_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    logger.info(
        "payment_failure_callback",
        extra={
            "chat_id": chat_id,
            "order_id": order_id,
        },
    )

    state = await get_state(chat_id=chat_id)

    if not state:
        logger.warning(
            "state_not_found_payment_failure",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    try:
        await fail_order_payment(
            payment_id=state.get("payment_id", 0),
        )

        logger.info(
            "order_payment_failed",
            extra={
                "chat_id": chat_id,
                "order_id": order_id,
            },
        )

    except Exception as e:
        logger.exception(
            "order_payment_fail_exception",
            extra={
                "chat_id": chat_id,
                "order_id": order_id,
                "error": str(e),
            },
        )

    state["payment_status"] = "failed"
    await set_state(chat_id=chat_id, state=state)

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text="❌ فشل الدفع. يرجى المحاولة مرة أخرى.",
        reply_markup=await payment_failed_ui(
            order_id=order_id,
            reason="payment_failed",
        ),
    )
