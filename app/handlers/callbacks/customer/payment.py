# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / CUSTOMER / PAYMENT
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for payment.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from app.core.database import get_session
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.core.middleware.rate_limit import rate_limit
from app.helpers.ui_manager import UIManager
from app.repositories.state_repo import (
    get_state,
    set_state,
)
from app.services.business.order_payments_service import OrderPaymentsService
from app.views.payment_ui import (
    payment_confirmation_ui,
    payment_failed_ui,
    payment_pending_ui,
    payment_success_ui,
    payment_ui,
)

# ==============================================
# 💳 PAYMENT METHOD SELECTED
# اختيار طريقة الدفع
# ==============================================


# ==============================================
# PAYMENT METHOD CALLBACK
# ==============================================


@rate_limit(
    limit=5,
    window=30,
    key_prefix="payment_method",
)
async def payment_method_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    معالجة اختيار طريقة الدفع من قبل الزبون
    """
    try:
        payment_method = match.group(0).split("_")[1]
        order_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "payment_method_invalid_callback",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    logger.info(
        "payment_method_selected",
        extra={
            "chat_id": chat_id,
            "order_id": order_id,
            "payment_method": payment_method,
        },
    )

    state = await get_state(chat_id=chat_id)

    if not state:
        logger.warning(
            "state_not_found_payment_method",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    try:
        async with await get_session() as session:
            total, allowed_methods = await OrderPaymentsService(
                session=session
            ).get_customer_payment_options(chat_id=chat_id, order_id=order_id)
        if payment_method not in allowed_methods:
            raise ValidationError(message="Payment method is unavailable")
    except (NotFoundError, ValidationError):
        await UIManager.edit(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ لا يمكن تسجيل الدفع لهذا الطلب بهذه الطريقة.",
            reply_markup=None,
        )
        return

    state["payment_method"] = payment_method
    state["order_id"] = order_id
    state["total_amount"] = total

    await set_state(
        chat_id=chat_id,
        state=state,
    )

    await UIManager.edit(
        chat_id=chat_id,
        message_id=message_id,
        text=(
            f"💳 **تأكيد الدفع**\n\n"
            f"طريقة الدفع: **{payment_method}**\n"
            f"المبلغ: **{total:.2f} دج**\n\n"
            f"هل تريد تسجيل طلب الدفع بهذه الطريقة؟"
        ),
        reply_markup=await payment_confirmation_ui(
            order_id=order_id,
            payment_method=payment_method,
            amount=total,
        ),
    )


# ==============================================
# ✅ PAYMENT CONFIRM
# تأكيد الدفع
# ==============================================


# ==============================================
# PAYMENT CONFIRM CALLBACK
# ==============================================


@rate_limit(
    limit=5,
    window=30,
    key_prefix="payment_confirm",
)
async def payment_confirm_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    تأكيد عملية الدفع
    """
    try:
        order_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "payment_confirm_invalid_order_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    logger.info(
        "payment_confirm_callback",
        extra={
            "chat_id": chat_id,
            "order_id": order_id,
        },
    )

    state = await get_state(chat_id=chat_id)

    if not state:
        logger.warning(
            "state_not_found_payment_confirm",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    payment_method = state.get("payment_method", "cash")
    total = state.get("total_amount", 0)

    try:
        async with await get_session() as session:
            payment = await OrderPaymentsService(
                session=session
            ).submit_customer_payment(
                chat_id=chat_id,
                order_id=order_id,
                payment_method=payment_method,
            )
        payment_id = payment.id
        total = payment.amount
        state["total_amount"] = total

        state["payment_id"] = payment_id
        state["payment_method"] = payment.payment_method

        logger.info(
            "payment_request_submitted",
            extra={
                "chat_id": chat_id,
                "order_id": order_id,
                "payment_id": payment_id,
                "payment_method": payment_method,
                "amount": total,
            },
        )

    except Exception as e:
        logger.exception(
            "payment_confirm_failed",
            extra={
                "chat_id": chat_id,
                "order_id": order_id,
                "error": str(e),
            },
        )

        await UIManager.edit(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ فشل تأكيد الدفع. يرجى المحاولة مرة أخرى.",
            reply_markup=await payment_failed_ui(
                order_id=order_id,
                reason=str(e),
            ),
        )
        return

    state["payment_status"] = payment.payment_status
    await set_state(chat_id=chat_id, state=state)
    if payment.payment_status == "paid":
        text = f"✅ تم التحقق من الدفع.\nالمبلغ: {total:.2f} دج"
        markup = await payment_success_ui(
            order_id=order_id, payment_method=payment.payment_method, amount=total
        )
    else:
        text = (
            f"🕒 تم تسجيل طلب الدفع.\nالمبلغ: {total:.2f} دج\n"
            "حالة الدفع: في انتظار التحقق من استلام المبلغ."
        )
        markup = await payment_pending_ui(order_id=order_id)
    await UIManager.edit(
        chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup
    )


# ==============================================
# 🔄 RETRY PAYMENT
# إعادة محاولة الدفع
# ==============================================


# ==============================================
# RETRY PAYMENT CALLBACK
# ==============================================


@rate_limit(
    limit=5,
    window=30,
    key_prefix="retry_payment",
)
async def retry_payment_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    إعادة محاولة الدفع بعد الفشل
    """
    try:
        order_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "retry_payment_invalid_order_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    logger.info(
        "retry_payment_callback",
        extra={
            "chat_id": chat_id,
            "order_id": order_id,
        },
    )

    state = await get_state(chat_id=chat_id)

    if not state:
        logger.warning(
            "state_not_found_retry_payment",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    try:
        async with await get_session() as session:
            total, allowed_methods = await OrderPaymentsService(
                session=session
            ).get_customer_payment_options(chat_id=chat_id, order_id=order_id)
    except (NotFoundError, ValidationError):
        await UIManager.edit(
            chat_id=chat_id,
            message_id=message_id,
            text="\u274c \u0644\u0627 \u064a\u0645\u0643\u0646 \u0627\u0644\u0648\u0635\u0648\u0644 \u0625\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u0637\u0644\u0628.",
            reply_markup=None,
        )
        return
    state["order_id"] = order_id
    state["total_amount"] = total
    await set_state(chat_id=chat_id, state=state)

    await UIManager.edit(
        chat_id=chat_id,
        message_id=message_id,
        text="💳 **اختر طريقة الدفع**",
        reply_markup=await payment_ui(
            allowed_methods=allowed_methods,
            order_id=order_id,
        ),
    )


# ==============================================
# 🔙 BACK TO PAYMENT
# الرجوع إلى واجهة الدفع
# ==============================================


# ==============================================
# BACK TO PAYMENT CALLBACK
# ==============================================


@rate_limit(
    limit=10,
    window=30,
    key_prefix="back_to_payment",
)
async def back_to_payment_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    الرجوع إلى واجهة اختيار طريقة الدفع
    """
    try:
        order_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "back_to_payment_invalid_order_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    logger.info(
        "back_to_payment_callback",
        extra={
            "chat_id": chat_id,
            "order_id": order_id,
        },
    )

    state = await get_state(chat_id=chat_id)

    if not state:
        logger.warning(
            "state_not_found_back_to_payment",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    try:
        async with await get_session() as session:
            total, allowed_methods = await OrderPaymentsService(
                session=session
            ).get_customer_payment_options(chat_id=chat_id, order_id=order_id)
    except (NotFoundError, ValidationError):
        await UIManager.edit(
            chat_id=chat_id,
            message_id=message_id,
            text="\u274c \u0644\u0627 \u064a\u0645\u0643\u0646 \u0627\u0644\u0648\u0635\u0648\u0644 \u0625\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u0637\u0644\u0628.",
            reply_markup=None,
        )
        return
    state["order_id"] = order_id
    state["total_amount"] = total
    await set_state(chat_id=chat_id, state=state)

    await UIManager.edit(
        chat_id=chat_id,
        message_id=message_id,
        text="💳 **اختر طريقة الدفع**",
        reply_markup=await payment_ui(
            allowed_methods=allowed_methods,
            order_id=order_id,
        ),
    )
