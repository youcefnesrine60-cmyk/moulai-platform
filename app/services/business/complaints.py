# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📣 CUSTOMER COMPLAINT OPERATIONS
# عمليات شكاوى العملاء
# يتضمن: إنشاء شكوى جديدة مع التحقق من البيانات
# ==============================================

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.logger import logger
from app.core.exceptions import NotFoundError, ValidationError
from app.models.complaint import Complaint
from app.models.restaurant import Restaurant
from app.models.user import User
from app.services.business.orders.customer import get_customer_order

# ==============================================
# 📋 CONSTANTS
# ==============================================

MAX_COMPLAINT_DESCRIPTION_LENGTH = 5000
"""الحد الأقصى لطول وصف الشكوى."""

# ==============================================
# 📋 TYPE ALIASES
# ==============================================

OrderReference = Any
"""مرجع الطلب: يمكن أن يكون رقم الطلب أو المعرف الرقمي."""

# ==============================================
# 🔍 BASE SELECT
# استعلام أساسي لجلب المستخدم بواسطة chat_id
# ==============================================

def _base_user_select() -> Select:
    """
    بناء استعلام أساسي لجلب المستخدم بواسطة معرف المحادثة.

    Returns:
        Select: استعلام SQLAlchemy الأساسي على جدول المستخدم.
    """
    return select(User)


# ==============================================
# 📣 CREATE CUSTOMER COMPLAINT
# إنشاء شكوى جديدة لعميل
# ==============================================

async def create_customer_complaint(
    *,
    chat_id: int,
    restaurant_id: Optional[int],
    order_reference: OrderReference,
    description: str,
    session: AsyncSession,
) -> Complaint:
    """
    إنشاء شكوى جديدة لعميل مع التحقق من البيانات والصلاحيات.

    Args:
        chat_id: معرف المحادثة في تيليجرام.
        restaurant_id: معرف المطعم المعني بالشكوى (اختياري إذا تم تمرير طلب).
        order_reference: مرجع الطلب المرتبط بالشكوى (اختياري).
        description: وصف الشكوى.
        session: جلسة قاعدة البيانات غير المتزامنة.

    Returns:
        Complaint: كائن الشكوى بعد الإنشاء.

    Raises:
        ValidationError: إذا كانت البيانات غير صالحة أو غير مكتملة.
        NotFoundError: إذا لم يتم العثور على المستخدم أو المطعم أو الطلب.
    """
    # ==========================================
    # ✅ VALIDATION
    # ==========================================

    normalized_description = description.strip()
    if (
        not normalized_description
        or len(normalized_description) > MAX_COMPLAINT_DESCRIPTION_LENGTH
    ):
        raise ValidationError(
            message=(
                f"وصف الشكوى مطلوب ويجب ألا يتجاوز "
                f"{MAX_COMPLAINT_DESCRIPTION_LENGTH} حرف."
            ),
            error_code="INVALID_COMPLAINT_DESCRIPTION",
        )

    async with session.begin():
        # ==========================================
        # 👤 FETCH USER
        # ==========================================

        user_result = await session.execute(
            _base_user_select().where(User.chat_id == chat_id),
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise NotFoundError(
                message="تعذر التحقق من حسابك.",
                error_code="USER_NOT_FOUND",
            )
        if not user.consent:
            raise ValidationError(
                message="يرجى الموافقة على شروط الاستخدام قبل إرسال الشكوى.",
                error_code="CUSTOMER_CONSENT_REQUIRED",
            )

        # ==========================================
        # 📦 FETCH ORDER (OPTIONAL)
        # ==========================================

        order = None
        if order_reference is not None and str(order_reference).strip():
            order = await get_customer_order(
                chat_id=chat_id,
                order_reference=order_reference,
                session=session,
            )
            if not order:
                raise NotFoundError(
                    message="لم أجد هذا الطلب ضمن طلبات حسابك.",
                    error_code="ORDER_NOT_FOUND",
                )
            if restaurant_id is not None and order.restaurant_id != restaurant_id:
                raise ValidationError(
                    message="الطلب لا ينتمي إلى المطعم المحدد.",
                    error_code="COMPLAINT_ORDER_RESTAURANT_MISMATCH",
                )
            restaurant_id = order.restaurant_id

        if restaurant_id is None:
            raise ValidationError(
                message="اختر المطعم الذي تريد تقديم الشكوى إليه.",
                error_code="COMPLAINT_RESTAURANT_REQUIRED",
            )

        # ==========================================
        # 🏪 FETCH RESTAURANT
        # ==========================================

        restaurant = await session.get(Restaurant, restaurant_id)
        if not restaurant:
            raise NotFoundError(
                message="المطعم المحدد غير موجود.",
                error_code="COMPLAINT_RESTAURANT_NOT_FOUND",
            )

        # ==========================================
        # 📣 CREATE COMPLAINT
        # ==========================================

        complaint = Complaint(
            user_id=user.id,
            restaurant_id=restaurant_id,
            order_id=order.id if order else None,
            description=normalized_description,
            status="open",
        )
        session.add(complaint)
        await session.flush()

    logger.info(
        "Customer complaint created",
        extra={
            "chat_id": chat_id,
            "complaint_id": complaint.id,
            "user_id": user.id,
            "restaurant_id": restaurant_id,
            "order_id": complaint.order_id,
        },
    )

    return complaint