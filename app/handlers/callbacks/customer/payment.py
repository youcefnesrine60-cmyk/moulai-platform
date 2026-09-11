# ==============================================
# 💳 PAYMENT CALLBACKS
# معالجة أزرار الدفع الخاصة بالزبون
# ==============================================

import re

from app.core.logger import logger
from app.core.middleware.rate_limit import rate_limit

from app.helpers.ui_manager import UIManager
from app.repositories.state_repo import get_state, set_state

from app.views.payment_ui import (
    payment_success_ui,
    payment_failed_ui,
    payment_confirmation_ui,
    payment_ui,
)

from app.services.business.payment_service import create_payment_request
from app.services.business.order_payments_service import (
    confirm_payment as confirm_order_payment,
    get_allowed_payment_methods_for_order,
)


# ==============================================
# 💳 PAYMENT METHOD SELECTED
# اختيار طريقة الدفع
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

    state["payment_method"] = payment_method
    state["order_id"] = order_id

    cart = state.get("cart", [])
    total = sum(
        float(item.get("price", 0))
        for item in cart
    )
    state["total_amount"] = total

    await set_state(
        chat_id=chat_id,
        state=state,
    )

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=(
            f"💳 **تأكيد الدفع**\n\n"
            f"طريقة الدفع: **{payment_method}**\n"
            f"المبلغ: **{total:.2f} دج**\n\n"
            f"هل أنت متأكد من إتمام عملية الدفع؟"
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

    # ✅ جلب owner_id و restaurant_id من الحالة مع قيم افتراضية آمنة
    owner_id = state.get("owner_id")
    restaurant_id = state.get("restaurant_id")

    # ✅ إذا لم تكن موجودة، نحاول جلبها من مصادر أخرى
    if not owner_id or not restaurant_id:
        # محاولة جلب restaurant_id من order_id
        from app.repositories.orders_repo import get_order
        order = await get_order(order_id=order_id)
        if order:
            restaurant_id = order.get("restaurant_id")
            # owner_id لا يمكن جلبها من order مباشرة، نحتاج إلى جلبها من restaurant
            if restaurant_id:
                from app.repositories.restaurant.restaurant_repo import get_restaurant_by_id
                restaurant = await get_restaurant_by_id(restaurant_id=restaurant_id)
                if restaurant:
                    owner_id = restaurant.get("owner_id")

    # ✅ إذا بقيت None، نستخدم قيماً افتراضية (مع تسجيل تحذير)
    if not owner_id:
        logger.warning(
            "owner_id_not_found_in_state",
            extra={
                "chat_id": chat_id,
                "order_id": order_id,
            },
        )
        # ✅ في هذه الحالة، نستخدم قيمة افتراضية مؤقتة (يجب تحديثها لاحقاً)
        owner_id = 1

    if not restaurant_id:
        logger.warning(
            "restaurant_id_not_found_in_state",
            extra={
                "chat_id": chat_id,
                "order_id": order_id,
            },
        )
        restaurant_id = 1

    # ==========================================
    # 💰 تنفيذ الدفع
    # ==========================================

    try:
        payment_id = await create_payment_request(
            owner_id=owner_id,
            restaurant_id=restaurant_id,
            subscription_id=None,
            payment_method=payment_method,
            amount=total,
        )

        await confirm_order_payment(
            payment_id=payment_id,
        )

        state["payment_id"] = payment_id

        logger.info(
            "payment_confirmed",
            extra={
                "chat_id": chat_id,
                "order_id": order_id,
                "payment_id": payment_id,
                "payment_method": payment_method,
                "amount": total,
                "owner_id": owner_id,
                "restaurant_id": restaurant_id,
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

        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ فشل تأكيد الدفع. يرجى المحاولة مرة أخرى.",
            reply_markup=await payment_failed_ui(
                order_id=order_id,
                reason=str(e),
            ),
        )
        return

    state["payment_status"] = "paid"
    await set_state(
        chat_id=chat_id,
        state=state,
    )

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=(
            f"✅ **تم الدفع بنجاح!**\n\n"
            f"💰 المبلغ: {total:.2f} دج\n"
            f"💳 طريقة الدفع: {payment_method}\n\n"
            f"📦 سيتم إشعارك عند تجهيز طلبك."
        ),
        reply_markup=await payment_success_ui(
            order_id=order_id,
            payment_method=payment_method,
            amount=total,
        ),
    )


# ==============================================
# 🔄 RETRY PAYMENT
# إعادة محاولة الدفع
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

    state["payment_status"] = "pending"
    await set_state(
        chat_id=chat_id,
        state=state,
    )

    allowed_methods = await get_allowed_payment_methods_for_order(
        order_id=order_id,
    )

    await UIManager.update(
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

    state["payment_status"] = "pending"
    await set_state(
        chat_id=chat_id,
        state=state,
    )

    allowed_methods = await get_allowed_payment_methods_for_order(
        order_id=order_id,
    )

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text="💳 **اختر طريقة الدفع**",
        reply_markup=await payment_ui(
            allowed_methods=allowed_methods,
            order_id=order_id,
        ),
    )