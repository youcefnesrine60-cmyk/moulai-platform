# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 💳 PAYMENT REPOSITORY
# عمليات قاعدة البيانات للمدفوعات باستخدام SQLAlchemy
# ==============================================

"""MoulAI operational module for payment repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.core.logger import logger
from app.models.payment import Payment
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

PaymentData = Dict[str, Any]
PaymentUpdateData = Dict[str, Any]
PaymentList = List[Payment]

# ==============================================
# 💳 PAYMENT REPOSITORY
# ==============================================


class PaymentRepository(BaseRepository[Payment, PaymentData, PaymentUpdateData]):
    """
    مستودع المدفوعات - يوفر عمليات خاصة بالمدفوعات.

    مسؤول عن:
        - عمليات CRUD الأساسية للمدفوعات
        - البحث والتصفية حسب المالك والمطعم والاشتراك
        - إدارة حالة المدفوعات (paid, failed, cancelled)
        - إحصائيات المدفوعات

    Attributes:
        model: نموذج Payment
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع المدفوعات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Payment, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY OWNER ID
    # ==============================================

    async def get_by_owner_id(
        self,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> PaymentList:
        """
        الحصول على مدفوعات مالك معين.

        Args:
            owner_id: معرف المالك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة المدفوعات
        """
        try:
            query = (
                select(self.model)
                .where(self.model.owner_id == owner_id)
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "payment_repo_get_by_owner_failed",
                extra={
                    "owner_id": owner_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY RESTAURANT ID
    # ==============================================

    async def get_by_restaurant_id(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> PaymentList:
        """
        الحصول على مدفوعات مطعم معين.

        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة المدفوعات
        """
        try:
            query = (
                select(self.model)
                .where(self.model.restaurant_id == restaurant_id)
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "payment_repo_get_by_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY SUBSCRIPTION ID
    # ==============================================

    async def get_by_subscription_id(
        self,
        *,
        subscription_id: int,
    ) -> PaymentList:
        """
        الحصول على مدفوعات اشتراك معين.

        Args:
            subscription_id: معرف الاشتراك

        Returns:
            قائمة المدفوعات
        """
        try:
            result = await self.session.execute(
                select(self.model)
                .where(self.model.subscription_id == subscription_id)
                .order_by(self.model.created_at.desc()),
            )

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "payment_repo_get_by_subscription_failed",
                extra={
                    "subscription_id": subscription_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY STATUS
    # ==============================================

    async def get_by_status(
        self,
        *,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> PaymentList:
        """
        الحصول على مدفوعات حسب الحالة.

        Args:
            status: حالة الدفع (pending, paid, failed, cancelled)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة المدفوعات
        """
        try:
            query = (
                select(self.model)
                .where(self.model.status == status)
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "payment_repo_get_by_status_failed",
                extra={
                    "status": status,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY EXTERNAL REFERENCE
    # ==============================================

    async def get_by_external_reference(
        self,
        *,
        external_reference: str,
    ) -> Optional[Payment]:
        """
        الحصول على دفع بواسطة المرجع الخارجي.

        Args:
            external_reference: المرجع الخارجي من بوابة الدفع

        Returns:
            كائن Payment أو None
        """
        try:
            result = await self.session.execute(
                select(self.model).where(
                    self.model.external_reference == external_reference
                ),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "payment_repo_get_by_reference_failed",
                extra={
                    "external_reference": external_reference,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET PENDING
    # ==============================================

    async def get_pending(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> PaymentList:
        """
        الحصول على المدفوعات المعلقة.

        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة المدفوعات المعلقة
        """
        return await self.get_by_status(
            status="pending",
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # SEARCH
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> PaymentList:
        """
        البحث عن مدفوعات.

        Args:
            query: نص البحث (في external_reference أو payment_method)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة المدفوعات
        """
        try:
            stmt = (
                select(self.model)
                .where(
                    or_(
                        self.model.external_reference.ilike(f"%{query}%"),
                        self.model.payment_method.ilike(f"%{query}%"),
                    ),
                )
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "payment_repo_search_failed",
                extra={
                    "query": query,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ UPDATES
    # ==========================================

    # ==============================================
    # UPDATE STATUS
    # ==============================================

    async def update_status(
        self,
        *,
        payment_id: int,
        status: str,
        paid_at: Optional[datetime] = None,
    ) -> Optional[Payment]:
        """
        تحديث حالة الدفع.

        Args:
            payment_id: معرف الدفع
            status: الحالة الجديدة (pending, paid, failed, cancelled)
            paid_at: تاريخ الدفع (إذا كان مدفوعاً)

        Returns:
            كائن Payment المحدث أو None
        """
        logger.info(
            "payment_repo_update_status",
            extra={
                "payment_id": payment_id,
                "status": status,
                "paid_at": paid_at,
            },
        )

        data: PaymentUpdateData = {"status": status}

        if paid_at is not None:
            data["paid_at"] = paid_at

        return await self.update(
            id=payment_id,
            data=data,
        )

    # ==============================================
    # MARK PAID
    # ==============================================

    async def mark_paid(
        self,
        *,
        payment_id: int,
        paid_at: Optional[datetime] = None,
    ) -> Optional[Payment]:
        """
        تعيين الدفع كمدفوع.

        Args:
            payment_id: معرف الدفع
            paid_at: تاريخ الدفع (افتراضي: الآن)

        Returns:
            كائن Payment المحدث أو None
        """
        if paid_at is None:
            paid_at = datetime.now()

        logger.info(
            "payment_repo_mark_paid",
            extra={
                "payment_id": payment_id,
                "paid_at": paid_at,
            },
        )

        return await self.update_status(
            payment_id=payment_id,
            status="paid",
            paid_at=paid_at,
        )

    # ==============================================
    # MARK FAILED
    # ==============================================

    async def mark_failed(
        self,
        *,
        payment_id: int,
    ) -> Optional[Payment]:
        """
        تعيين الدفع كفاشل.

        Args:
            payment_id: معرف الدفع

        Returns:
            كائن Payment المحدث أو None
        """
        logger.info(
            "payment_repo_mark_failed",
            extra={"payment_id": payment_id},
        )

        return await self.update_status(
            payment_id=payment_id,
            status="failed",
        )

    # ==============================================
    # MARK CANCELLED
    # ==============================================

    async def mark_cancelled(
        self,
        *,
        payment_id: int,
    ) -> Optional[Payment]:
        """
        إلغاء الدفع.

        Args:
            payment_id: معرف الدفع

        Returns:
            كائن Payment المحدث أو None
        """
        logger.info(
            "payment_repo_mark_cancelled",
            extra={"payment_id": payment_id},
        )

        return await self.update_status(
            payment_id=payment_id,
            status="cancelled",
        )

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY STATUS
    # ==============================================

    async def count_by_status(
        self,
        *,
        status: str,
    ) -> int:
        """
        حساب عدد المدفوعات حسب الحالة.

        Args:
            status: حالة الدفع

        Returns:
            عدد المدفوعات
        """
        return await self.count(filters={"status": status})

    # ==============================================
    # COUNT BY OWNER
    # ==============================================

    async def count_by_owner(
        self,
        *,
        owner_id: int,
    ) -> int:
        """
        حساب عدد مدفوعات مالك معين.

        Args:
            owner_id: معرف المالك

        Returns:
            عدد المدفوعات
        """
        return await self.count(filters={"owner_id": owner_id})

    # ==============================================
    # COUNT BY RESTAURANT
    # ==============================================

    async def count_by_restaurant(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        حساب عدد مدفوعات مطعم معين.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            عدد المدفوعات
        """
        return await self.count(filters={"restaurant_id": restaurant_id})

    # ==============================================
    # TOTAL AMOUNT BY OWNER
    # ==============================================

    async def total_amount_by_owner(
        self,
        *,
        owner_id: int,
        status: Optional[str] = "paid",
    ) -> float:
        """
        حساب إجمالي المدفوعات لمالك معين.

        Args:
            owner_id: معرف المالك
            status: حالة الدفع (اختياري)

        Returns:
            إجمالي المبلغ
        """
        try:
            query = select(func.sum(self.model.amount)).where(
                self.model.owner_id == owner_id,
            )

            if status:
                query = query.where(self.model.status == status)

            result = await self.session.execute(query)
            total = result.scalar_one()

            return float(total) if total else 0.0

        except Exception as e:
            logger.exception(
                "payment_repo_total_amount_by_owner_failed",
                extra={
                    "owner_id": owner_id,
                    "error": str(e),
                },
            )
            raise


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE PAYMENT (COMPATIBILITY)
# ==============================================


async def create_payment(
    *,
    owner_id: int,
    restaurant_id: int,
    subscription_id: Optional[int],
    payment_method: str,
    amount: float,
    status: str = "pending",
    external_reference: Optional[str] = None,
    session: AsyncSession,
) -> int:
    """
    إنشاء دفع جديد (دالة متوافقة مع الإصدار القديم).

    Args:
        owner_id: معرف المالك
        restaurant_id: معرف المطعم
        subscription_id: معرف الاشتراك
        payment_method: طريقة الدفع
        amount: المبلغ
        status: حالة الدفع
        external_reference: المرجع الخارجي
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف الدفع
    """
    repo = PaymentRepository(session=session)

    data: PaymentData = {
        "owner_id": owner_id,
        "restaurant_id": restaurant_id,
        "subscription_id": subscription_id,
        "payment_method": payment_method,
        "amount": amount,
        "status": status,
        "external_reference": external_reference,
    }

    payment = await repo.create(data=data)

    logger.info(
        "payment_created",
        extra={
            "payment_id": payment.id,
            "owner_id": owner_id,
            "restaurant_id": restaurant_id,
        },
    )

    return payment.id


# ==============================================
# GET PAYMENT BY ID (COMPATIBILITY)
# ==============================================


async def get_payment_by_id(
    *,
    payment_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على دفع بالمعرف (دالة متوافقة مع الإصدار القديم).

    Args:
        payment_id: معرف الدفع
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات الدفع أو None
    """
    repo = PaymentRepository(session=session)

    payment = await repo.get_by_id(id=payment_id)

    if not payment:
        return None

    return {
        "id": payment.id,
        "owner_id": payment.owner_id,
        "restaurant_id": payment.restaurant_id,
        "subscription_id": payment.subscription_id,
        "payment_method": payment.payment_method,
        "amount": payment.amount,
        "status": payment.status,
        "external_reference": payment.external_reference,
        "created_at": payment.created_at,
        "paid_at": payment.paid_at,
    }


# ==============================================
# GET PAYMENT BY REFERENCE (COMPATIBILITY)
# ==============================================


async def get_payment_by_reference(
    *,
    external_reference: str,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على دفع بواسطة المرجع الخارجي (دالة متوافقة مع الإصدار القديم).

    Args:
        external_reference: المرجع الخارجي
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات الدفع أو None
    """
    repo = PaymentRepository(session=session)

    payment = await repo.get_by_external_reference(
        external_reference=external_reference,
    )

    if not payment:
        return None

    return {
        "id": payment.id,
        "owner_id": payment.owner_id,
        "restaurant_id": payment.restaurant_id,
        "subscription_id": payment.subscription_id,
        "payment_method": payment.payment_method,
        "amount": payment.amount,
        "status": payment.status,
        "external_reference": payment.external_reference,
        "created_at": payment.created_at,
        "paid_at": payment.paid_at,
    }


# ==============================================
# MARK PAYMENT PAID (COMPATIBILITY)
# ==============================================


async def mark_payment_paid(
    *,
    payment_id: int,
    paid_at: datetime,
    session: AsyncSession,
) -> None:
    """
    تعيين الدفع كمدفوع (دالة متوافقة مع الإصدار القديم).

    Args:
        payment_id: معرف الدفع
        paid_at: تاريخ الدفع
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = PaymentRepository(session=session)

    await repo.mark_paid(
        payment_id=payment_id,
        paid_at=paid_at,
    )

    logger.info(
        "payment_marked_paid",
        extra={"payment_id": payment_id},
    )


# ==============================================
# MARK PAYMENT FAILED (COMPATIBILITY)
# ==============================================


async def mark_payment_failed(
    *,
    payment_id: int,
    session: AsyncSession,
) -> None:
    """
    تعيين الدفع كفاشل (دالة متوافقة مع الإصدار القديم).

    Args:
        payment_id: معرف الدفع
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = PaymentRepository(session=session)

    await repo.mark_failed(payment_id=payment_id)

    logger.info(
        "payment_marked_failed",
        extra={"payment_id": payment_id},
    )


# ==============================================
# CANCEL PAYMENT (COMPATIBILITY)
# ==============================================


async def cancel_payment(
    *,
    payment_id: int,
    session: AsyncSession,
) -> None:
    """
    إلغاء الدفع (دالة متوافقة مع الإصدار القديم).

    Args:
        payment_id: معرف الدفع
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = PaymentRepository(session=session)

    await repo.mark_cancelled(payment_id=payment_id)

    logger.info(
        "payment_cancelled",
        extra={"payment_id": payment_id},
    )


# ==============================================
# GET OWNER PAYMENTS (COMPATIBILITY)
# ==============================================


async def get_owner_payments(
    *,
    owner_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على مدفوعات مالك معين (دالة متوافقة مع الإصدار القديم).

    Args:
        owner_id: معرف المالك
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        قائمة المدفوعات
    """
    repo = PaymentRepository(session=session)

    payments = await repo.get_by_owner_id(
        owner_id=owner_id,
        skip=skip,
        limit=limit,
    )

    result = []

    for payment in payments:
        result.append(
            {
                "id": payment.id,
                "owner_id": payment.owner_id,
                "restaurant_id": payment.restaurant_id,
                "subscription_id": payment.subscription_id,
                "payment_method": payment.payment_method,
                "amount": payment.amount,
                "status": payment.status,
                "external_reference": payment.external_reference,
                "created_at": payment.created_at,
                "paid_at": payment.paid_at,
            }
        )

    return result


# ==============================================
# GET RESTAURANT PAYMENTS (COMPATIBILITY)
# ==============================================


async def get_restaurant_payments(
    *,
    restaurant_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على مدفوعات مطعم معين (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        قائمة المدفوعات
    """
    repo = PaymentRepository(session=session)

    payments = await repo.get_by_restaurant_id(
        restaurant_id=restaurant_id,
        skip=skip,
        limit=limit,
    )

    result = []

    for payment in payments:
        result.append(
            {
                "id": payment.id,
                "owner_id": payment.owner_id,
                "restaurant_id": payment.restaurant_id,
                "subscription_id": payment.subscription_id,
                "payment_method": payment.payment_method,
                "amount": payment.amount,
                "status": payment.status,
                "external_reference": payment.external_reference,
                "created_at": payment.created_at,
                "paid_at": payment.paid_at,
            }
        )

    return result


# ==============================================
# 🔄 TRANSACTION FUNCTIONS
# (للتوافق مع الكود القديم)
# ==============================================

# ==============================================
# CONFIRM PAYMENT TRANSACTIONS (COMPATIBILITY)
# ==============================================


async def confirm_payment_tx(
    *,
    conn: AsyncConnection,
    payment_id: int,
) -> int:
    """
    تأكيد الدفع (معاملة) - دالة متوافقة مع الإصدار القديم.

    Args:
        conn: اتصال قاعدة البيانات (غير مستخدم في SQLAlchemy)
        payment_id: معرف الدفع

    Returns:
        int: عدد الصفوف المتأثرة
    """
    # في SQLAlchemy، نستخدم session مباشرة
    repo = PaymentRepository(conn)  # conn هو AsyncSession في الواقع
    payment = await repo.mark_paid(payment_id)
    return 1 if payment else 0


# ==============================================
# FAIL PAYMENT TRANSACTIONS (COMPATIBILITY)
# ==============================================


async def fail_payment_tx(
    *,
    conn: AsyncConnection,
    payment_id: int,
) -> None:
    """
    تعيين الدفع كفاشل (معاملة) - دالة متوافقة مع الإصدار القديم.

    Args:
        conn: اتصال قاعدة البيانات (غير مستخدم في SQLAlchemy)
        payment_id: معرف الدفع
    """
    # في SQLAlchemy، نستخدم session مباشرة
    repo = PaymentRepository(conn)  # conn هو AsyncSession في الواقع
    await repo.mark_failed(payment_id)
