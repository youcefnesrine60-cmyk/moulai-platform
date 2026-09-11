# ==============================================
# 🛡️ ADMIN HANDLERS
# معالجات المسؤول (محدثة)
# ==============================================

import re

from app.core.logger import logger
from app.core.middleware.rate_limit import rate_limit

from app.helpers.ui_manager import UIManager

from app.repositories.registration_request_repo import (
    get_pending_requests,
    get_registration_request_by_id,
)

from app.repositories.restaurant.restaurant_repo import get_all_restaurants
from app.repositories.owner_repo import get_all_owners
from app.repositories.orders_repo import get_restaurant_orders

from app.services.business.registration_request_service import (
    approve_registration,
    reject_registration,
)

from app.services.business.admin.admin_service import (
    is_admin,
    count_admins,
)

from app.views.admin_ui import (
    admin_dashboard_ui,
    admin_requests_ui,
    admin_request_details_ui,
)


# ==============================================
# 🛡️ ADMIN DASHBOARD
# ==============================================

@rate_limit(
    limit=10,
    window=30,
    key_prefix="admin_dashboard",
)
async def admin_dashboard_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    عرض لوحة تحكم المسؤول
    """
    # ==========================================
    # 🔒 التحقق من صلاحية المسؤول
    # ==========================================

    if not await is_admin(chat_id=chat_id):
        logger.warning(
            "unauthorized_admin_access",
            extra={
                "chat_id": chat_id,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="⛔ غير مصرح لك بالوصول إلى لوحة المسؤول.",
            reply_markup=None,
        )
        return

    logger.info(
        "admin_dashboard_callback",
        extra={
            "chat_id": chat_id,
        },
    )

    # ==========================================
    # 📊 جلب الإحصائيات
    # ==========================================

    pending_requests = await get_pending_requests()

    restaurants = await get_all_restaurants()
    owners = await get_all_owners()

    # حساب عدد الطلبات (تقريبي)
    total_orders = 0
    for restaurant in restaurants:
        orders = await get_restaurant_orders(
            restaurant_id=restaurant["id"],
        )
        total_orders += len(orders)

    total_admins = await count_admins()

    # ==========================================
    # 🖥️ عرض لوحة التحكم
    # ==========================================

    dashboard_ui = await admin_dashboard_ui(
        pending_requests=len(pending_requests),
        total_restaurants=len(restaurants),
        total_owners=len(owners),
        total_orders=total_orders,
        total_admins=total_admins,
    )

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=dashboard_ui.get("text", "🛡️ لوحة تحكم المسؤول"),
        reply_markup=dashboard_ui.get("inline_keyboard"),
    )


# ==============================================
# 📋 ADMIN REQUESTS
# عرض طلبات التسجيل المعلقة
# ==============================================

@rate_limit(
    limit=10,
    window=30,
    key_prefix="admin_requests",
)
async def admin_requests_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    عرض طلبات التسجيل المعلقة
    """
    # 🔒 التحقق من صلاحية المسؤول
    if not await is_admin(chat_id=chat_id):
        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="⛔ غير مصرح لك بالوصول.",
            reply_markup=None,
        )
        return

    logger.info(
        "admin_requests_callback",
        extra={
            "chat_id": chat_id,
        },
    )

    pending_requests = await get_pending_requests()

    requests_ui = await admin_requests_ui(
        requests=pending_requests,
    )

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=requests_ui.get("text", "📋 طلبات التسجيل"),
        reply_markup=requests_ui.get("inline_keyboard"),
    )


# ==============================================
# 📋 ADMIN REQUEST DETAILS
# عرض تفاصيل طلب تسجيل معين
# ==============================================

@rate_limit(
    limit=10,
    window=30,
    key_prefix="admin_request_details",
)
async def admin_request_details_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    عرض تفاصيل طلب تسجيل معين
    """
    # 🔒 التحقق من صلاحية المسؤول
    if not await is_admin(chat_id=chat_id):
        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="⛔ غير مصرح لك بالوصول.",
            reply_markup=None,
        )
        return

    # استخراج معرف الطلب
    try:
        request_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "admin_request_details_invalid_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    logger.info(
        "admin_request_details_callback",
        extra={
            "chat_id": chat_id,
            "request_id": request_id,
        },
    )

    # جلب تفاصيل الطلب
    request = await get_registration_request_by_id(
        request_id=request_id,
    )

    if not request:
        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ طلب التسجيل غير موجود.",
            reply_markup=None,
        )
        return

    details_ui = await admin_request_details_ui(
        request=request,
    )

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=details_ui.get("text", "📋 تفاصيل الطلب"),
        reply_markup=details_ui.get("inline_keyboard"),
    )


# ==============================================
# ✅ ADMIN APPROVE REQUEST
# الموافقة على طلب تسجيل
# ==============================================

@rate_limit(
    limit=5,
    window=30,
    key_prefix="admin_approve",
)
async def admin_approve_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    الموافقة على طلب تسجيل
    """
    # 🔒 التحقق من صلاحية المسؤول
    if not await is_admin(chat_id=chat_id):
        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="⛔ غير مصرح لك بالوصول.",
            reply_markup=None,
        )
        return

    # استخراج معرف الطلب
    try:
        request_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "admin_approve_invalid_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    logger.info(
        "admin_approve_callback",
        extra={
            "chat_id": chat_id,
            "request_id": request_id,
        },
    )

    try:
        result = await approve_registration(
            request_id=request_id,
        )

        logger.info(
            "registration_approved_by_admin",
            extra={
                "chat_id": chat_id,
                "request_id": request_id,
                "owner_id": result.get("owner_id"),
                "restaurant_id": result.get("restaurant_id"),
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                f"✅ تمت الموافقة على طلب التسجيل #{request_id} بنجاح.\n\n"
                f"👤 تم إنشاء المالك.\n"
                f"🏪 تم إنشاء المطعم.\n"
                f"💳 تم تفعيل الاشتراك التجريبي."
            ),
            reply_markup=None,
        )

    except Exception as e:
        logger.exception(
            "admin_approve_failed",
            extra={
                "chat_id": chat_id,
                "request_id": request_id,
                "error": str(e),
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text=f"❌ فشلت الموافقة على الطلب: {str(e)}",
            reply_markup=None,
        )


# ==============================================
# ❌ ADMIN REJECT REQUEST
# رفض طلب تسجيل
# ==============================================

@rate_limit(
    limit=5,
    window=30,
    key_prefix="admin_reject",
)
async def admin_reject_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    رفض طلب تسجيل
    """
    # 🔒 التحقق من صلاحية المسؤول
    if not await is_admin(chat_id=chat_id):
        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="⛔ غير مصرح لك بالوصول.",
            reply_markup=None,
        )
        return

    # استخراج معرف الطلب
    try:
        request_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "admin_reject_invalid_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    logger.info(
        "admin_reject_callback",
        extra={
            "chat_id": chat_id,
            "request_id": request_id,
        },
    )

    try:
        await reject_registration(
            request_id=request_id,
        )

        logger.info(
            "registration_rejected_by_admin",
            extra={
                "chat_id": chat_id,
                "request_id": request_id,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text=f"❌ تم رفض طلب التسجيل #{request_id}.",
            reply_markup=None,
        )

    except Exception as e:
        logger.exception(
            "admin_reject_failed",
            extra={
                "chat_id": chat_id,
                "request_id": request_id,
                "error": str(e),
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text=f"❌ فشل رفض الطلب: {str(e)}",
            reply_markup=None,
        )