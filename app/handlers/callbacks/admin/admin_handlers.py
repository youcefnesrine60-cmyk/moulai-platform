# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / ADMIN / ADMIN HANDLERS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for admin handlers.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from app.core.database import get_session
from app.core.exceptions import NotFoundError
from app.core.logger import logger
from app.core.middleware.rate_limit import rate_limit
from app.helpers.ui_manager import UIManager
from app.repositories.orders_repo import OrdersRepository
from app.repositories.restaurant.restaurant_repo import RestaurantRepository
from app.services.business.admin.admin_service import AdminService
from app.services.business.owner_service import OwnerService
from app.services.business.registration_request_service import (
    RegistrationRequestService,
)
from app.views.admin_ui import (
    admin_dashboard_ui,
    admin_request_details_ui,
    admin_requests_ui,
)

# ==============================================
# AUTHORIZATION HELPERS
# ==============================================


async def _has_active_admin(
    *,
    chat_id: int,
) -> bool:
    """Resolve active administrator access through the SQLAlchemy service contract."""
    async with await get_session() as session:
        return await AdminService(session).has_active_chat(chat_id=chat_id)

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

    if not await _has_active_admin(chat_id=chat_id):
        logger.warning(
            "unauthorized_admin_access",
            extra={
                "chat_id": chat_id,
            },
        )

        await UIManager.edit(
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

    async with await get_session() as session:
        registration_service = RegistrationRequestService(session)
        pending_requests = [
            request.model_dump()
            for request in await registration_service.get_pending()
        ]
        restaurant_models = await RestaurantRepository(session).get_all(order_by="name")
        orders_repo = OrdersRepository(session)
        total_orders = sum(
            [
                await orders_repo.count(filters={"restaurant_id": restaurant.id})
                for restaurant in restaurant_models
            ],
        )
        total_owners = await OwnerService(session=session).count_owners()
        total_admins = await AdminService(session).count_admins()

    restaurants = [{"id": restaurant.id} for restaurant in restaurant_models]

    # ==========================================
    # 🖥️ عرض لوحة التحكم
    # ==========================================

    dashboard_ui = await admin_dashboard_ui(
        pending_requests=len(pending_requests),
        total_restaurants=len(restaurants),
        total_owners=total_owners,
        total_orders=total_orders,
        total_admins=total_admins,
    )

    await UIManager.edit(
        chat_id=chat_id,
        message_id=message_id,
        text=dashboard_ui.get("text", "🛡️ لوحة تحكم المسؤول"),
        reply_markup=dashboard_ui.get("inline_keyboard"),
    )


# ==============================================
# 📋 ADMIN REQUESTS
# عرض طلبات التسجيل المعلقة
# ==============================================


# ==============================================
# ADMIN REQUESTS CALLBACK
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
    if not await _has_active_admin(chat_id=chat_id):
        await UIManager.edit(
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

    async with await get_session() as session:
        registration_service = RegistrationRequestService(session)
        pending_requests = [
            request.model_dump()
            for request in await registration_service.get_pending()
        ]

    requests_ui = await admin_requests_ui(
        requests=pending_requests,
    )

    await UIManager.edit(
        chat_id=chat_id,
        message_id=message_id,
        text=requests_ui.get("text", "📋 طلبات التسجيل"),
        reply_markup=requests_ui.get("inline_keyboard"),
    )


# ==============================================
# 📋 ADMIN REQUEST DETAILS
# عرض تفاصيل طلب تسجيل معين
# ==============================================


# ==============================================
# ADMIN REQUEST DETAILS CALLBACK
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
    if not await _has_active_admin(chat_id=chat_id):
        await UIManager.edit(
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
    try:
        async with await get_session() as session:
            request = (
                await RegistrationRequestService(session).get_by_id(
                    request_id=request_id,
                )
            ).model_dump()
    except NotFoundError:
        await UIManager.edit(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ طلب التسجيل غير موجود.",
            reply_markup=None,
        )
        return

    details_ui = await admin_request_details_ui(
        request=request,
    )

    await UIManager.edit(
        chat_id=chat_id,
        message_id=message_id,
        text=details_ui.get("text", "📋 تفاصيل الطلب"),
        reply_markup=details_ui.get("inline_keyboard"),
    )


# ==============================================
# ✅ ADMIN APPROVE REQUEST
# الموافقة على طلب تسجيل
# ==============================================


# ==============================================
# ADMIN APPROVE CALLBACK
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
    if not await _has_active_admin(chat_id=chat_id):
        await UIManager.edit(
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
        async with await get_session() as session:
            result = await RegistrationRequestService(session).approve(
                request_id=request_id,
            )
            await session.commit()

        logger.info(
            "registration_approved_by_admin",
            extra={
                "chat_id": chat_id,
                "request_id": request_id,
                "owner_id": result.owner_id,
            },
        )

        await UIManager.edit(
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

        await UIManager.edit(
            chat_id=chat_id,
            message_id=message_id,
            text=f"❌ فشلت الموافقة على الطلب: {e!s}",
            reply_markup=None,
        )


# ==============================================
# ❌ ADMIN REJECT REQUEST
# رفض طلب تسجيل
# ==============================================


# ==============================================
# ADMIN REJECT CALLBACK
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
    if not await _has_active_admin(chat_id=chat_id):
        await UIManager.edit(
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
        async with await get_session() as session:
            await RegistrationRequestService(session).reject(
                request_id=request_id,
            )
            await session.commit()

        logger.info(
            "registration_rejected_by_admin",
            extra={
                "chat_id": chat_id,
                "request_id": request_id,
            },
        )

        await UIManager.edit(
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

        await UIManager.edit(
            chat_id=chat_id,
            message_id=message_id,
            text=f"❌ فشل رفض الطلب: {e!s}",
            reply_markup=None,
        )
