from sqlalchemy.orm import raiseload, selectinload
# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 💳 ORDER PAYMENTS REPOSITORY
# عمليات قاعدة البيانات لمدفوعات الطلبات باستخدام SQLAlchemy
# ==============================================

from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.order_item import OrderPayment
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

OrderPaymentData = Dict[str, Any]
OrderPaymentUpdateData = Dict[str, Any]
OrderPaymentList = List[OrderPayment]
OrderPaymentSummary = Dict[str, Any]

# ==============================================
# 💳 ORDER PAYMENTS REPOSITORY
# ==============================================


class OrderPaymentsRepository(
    BaseRepository[
        OrderPayment,
        OrderPaymentData,
        OrderPaymentUpdateData,
    ]
):
    """
    مستودع مدفوعات الطلبات - يوفر عمليات خاصة بمدفوعات الطلبات.
    
    مسؤول عن:
        - عمليات CRUD الأساسية لمدفوعات الطلبات
        - تحديث حالة الدفع
        - إحصائيات المدفوعات
    
    Attributes:
        model: نموذج OrderPayment
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع مدفوعات الطلبات.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(OrderPayment, session)
        self.commit_on_write = False
        self.query_options = [raiseload("*")]

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ORDER ID
    # ==============================================

    async def get_by_order_id(
        self,
        *,
        order_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> OrderPaymentList:
        """
        الحصول على مدفوعات طلب معين.
        
        Args:
            order_id: معرف الطلب
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة مدفوعات الطلب
        """
        try:
            query = (
                self._select()
                .where(self.model.order_id == order_id)
                .order_by(self.model.id.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "order_payments_repo_get_by_order_failed",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY TRANSACTION REFERENCE
    # ==============================================

    async def get_by_transaction_reference(
        self,
        *,
        transaction_reference: str,
    ) -> Optional[OrderPayment]:
        """
        الحصول على دفع بواسطة مرجع المعاملة.
        
        Args:
            transaction_reference: مرجع المعاملة
            
        Returns:
            كائن OrderPayment أو None
        """
        try:
            result = await self.session.execute(
                self._select()
                .where(self.model.transaction_reference == transaction_reference)
                .limit(1),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "order_payments_repo_get_by_reference_failed",
                extra={
                    "transaction_reference": transaction_reference,
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
        payment_status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> OrderPaymentList:
        """
        الحصول على مدفوعات حسب الحالة.
        
        Args:
            payment_status: حالة الدفع (pending, paid, failed, cancelled)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة المدفوعات
        """
        try:
            query = (
                self._select()
                .where(self.model.payment_status == payment_status)
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "order_payments_repo_get_by_status_failed",
                extra={
                    "payment_status": payment_status,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # COUNT BY ORDER
    # ==============================================

    async def count_by_order(
        self,
        *,
        order_id: int,
    ) -> int:
        """
        حساب عدد مدفوعات طلب معين.
        
        Args:
            order_id: معرف الطلب
            
        Returns:
            عدد المدفوعات
        """
        try:
            result = await self.session.execute(
                select(func.count())
                .select_from(self.model)
                .where(self.model.order_id == order_id),
            )

            return result.scalar_one()

        except Exception as e:
            logger.exception(
                "order_payments_repo_count_by_order_failed",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET TOTAL AMOUNT BY ORDER
    # ==============================================

    async def get_total_amount_by_order(
        self,
        *,
        order_id: int,
        payment_status: Optional[str] = "paid",
    ) -> float:
        """
        حساب إجمالي مبلغ مدفوعات طلب معين.
        
        Args:
            order_id: معرف الطلب
            payment_status: حالة الدفع (اختياري)
            
        Returns:
            إجمالي المبلغ
        """
        try:
            query = select(func.coalesce(func.sum(self.model.amount), 0)).where(
                self.model.order_id == order_id,
            )

            if payment_status is not None:
                query = query.where(self.model.payment_status == payment_status)

            result = await self.session.execute(query)

            return float(result.scalar_one())

        except Exception as e:
            logger.exception(
                "order_payments_repo_get_total_amount_by_order_failed",
                extra={
                    "order_id": order_id,
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
        payment_status: str,
        paid_at: Optional[datetime] = None,
    ) -> Optional[OrderPayment]:
        """
        تحديث حالة الدفع.
        
        Args:
            payment_id: معرف الدفع
            payment_status: الحالة الجديدة (pending, paid, failed, cancelled)
            paid_at: تاريخ الدفع (اختياري)
            
        Returns:
            كائن OrderPayment المحدث أو None
        """
        logger.info(
            "order_payments_repo_update_status",
            extra={
                "payment_id": payment_id,
                "payment_status": payment_status,
                "paid_at": paid_at,
            },
        )

        data: OrderPaymentUpdateData = {"payment_status": payment_status}

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
    ) -> Optional[OrderPayment]:
        """
        تعيين الدفع كمدفوع.
        
        Args:
            payment_id: معرف الدفع
            paid_at: تاريخ الدفع (افتراضي: الآن)
            
        Returns:
            كائن OrderPayment المحدث أو None
        """
        if paid_at is None:
            paid_at = datetime.now()

        logger.info(
            "order_payments_repo_mark_paid",
            extra={"payment_id": payment_id},
        )

        return await self.update_status(
            payment_id=payment_id,
            payment_status="paid",
            paid_at=paid_at,
        )

    # ==============================================
    # MARK FAILED
    # ==============================================

    async def mark_failed(
        self,
        *,
        payment_id: int,
    ) -> Optional[OrderPayment]:
        """
        تعيين الدفع كفاشل.
        
        Args:
            payment_id: معرف الدفع
            
        Returns:
            كائن OrderPayment المحدث أو None
        """
        logger.info(
            "order_payments_repo_mark_failed",
            extra={"payment_id": payment_id},
        )

        return await self.update_status(
            payment_id=payment_id,
            payment_status="failed",
        )

    # ==============================================
    # MARK CANCELLED
    # ==============================================

    async def mark_cancelled(
        self,
        *,
        payment_id: int,
    ) -> Optional[OrderPayment]:
        """
        إلغاء الدفع.
        
        Args:
            payment_id: معرف الدفع
            
        Returns:
            كائن OrderPayment المحدث أو None
        """
        logger.info(
            "order_payments_repo_mark_cancelled",
            extra={"payment_id": payment_id},
        )

        return await self.update_status(
            payment_id=payment_id,
            payment_status="cancelled",
        )

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # GET PAYMENT SUMMARY BY ORDER
    # ==============================================

    async def get_payment_summary_by_order(
        self,
        *,
        order_id: int,
    ) -> OrderPaymentSummary:
        """
        الحصول على ملخص مدفوعات طلب معين.
        
        Args:
            order_id: معرف الطلب
            
        Returns:
            قاموس ملخص المدفوعات
        """
        try:
            payments = await self.get_by_order_id(order_id=order_id)

            total_payments = len(payments)
            total_paid = sum(1 for p in payments if p.payment_status == "paid")
            total_pending = sum(1 for p in payments if p.payment_status == "pending")
            total_failed = sum(1 for p in payments if p.payment_status == "failed")
            total_cancelled = sum(1 for p in payments if p.payment_status == "cancelled")

            total_amount = sum(p.amount for p in payments)
            total_paid_amount = sum(p.amount for p in payments if p.payment_status == "paid")

            return {
                "order_id": order_id,
                "total_payments": total_payments,
                "total_paid": total_paid,
                "total_pending": total_pending,
                "total_failed": total_failed,
                "total_cancelled": total_cancelled,
                "total_amount": total_amount,
                "total_paid_amount": total_paid_amount,
            }

        except Exception as e:
            logger.exception(
                "order_payments_repo_get_payment_summary_failed",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            raise


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE ORDER PAYMENT (COMPATIBILITY)
# ==============================================

async def create_order_payment(
    *,
    order_id: int,
    payment_method: str,
    payment_status: str,
    amount: float,
    transaction_reference: Optional[str] = None,
    session: AsyncSession,
) -> int:
    """
    إنشاء دفع جديد للطلب (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        payment_method: طريقة الدفع
        payment_status: حالة الدفع
        amount: المبلغ
        transaction_reference: مرجع المعاملة
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        معرف الدفع
    """
    repo = OrderPaymentsRepository(session=session)

    data: OrderPaymentData = {
        "order_id": order_id,
        "payment_method": payment_method,
        "payment_status": payment_status,
        "amount": amount,
        "transaction_reference": transaction_reference,
    }

    payment = await repo.create(data=data)

    logger.info(
        "order_payment_created",
        extra={
            "payment_id": payment.id,
            "order_id": order_id,
        },
    )

    return payment.id


# ==============================================
# GET ORDER PAYMENT (COMPATIBILITY)
# ==============================================

async def get_order_payment(
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
    repo = OrderPaymentsRepository(session=session)

    payment = await repo.get_by_id(id=payment_id)

    if not payment:
        return None

    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "payment_method": payment.payment_method,
        "payment_status": payment.payment_status,
        "amount": payment.amount,
        "transaction_reference": payment.transaction_reference,
        "paid_at": payment.paid_at,
        "created_at": payment.created_at,
    }


# ==============================================
# GET ORDER PAYMENTS (COMPATIBILITY)
# ==============================================

async def get_order_payments(
    *,
    order_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على مدفوعات طلب معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        قائمة مدفوعات الطلب
    """
    repo = OrderPaymentsRepository(session=session)

    payments = await repo.get_by_order_id(
        order_id=order_id,
        skip=skip,
        limit=limit,
    )

    result = []

    for payment in payments:
        result.append({
            "id": payment.id,
            "order_id": payment.order_id,
            "payment_method": payment.payment_method,
            "payment_status": payment.payment_status,
            "amount": payment.amount,
            "transaction_reference": payment.transaction_reference,
            "paid_at": payment.paid_at,
            "created_at": payment.created_at,
        })

    return result


# ==============================================
# GET PAYMENT BY REFERENCE (COMPATIBILITY)
# ==============================================

async def get_payment_by_reference(
    *,
    transaction_reference: str,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على دفع بواسطة مرجع المعاملة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        transaction_reference: مرجع المعاملة
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قاموس بيانات الدفع أو None
    """
    repo = OrderPaymentsRepository(session=session)

    payment = await repo.get_by_transaction_reference(
        transaction_reference=transaction_reference,
    )

    if not payment:
        return None

    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "payment_method": payment.payment_method,
        "payment_status": payment.payment_status,
        "amount": payment.amount,
        "transaction_reference": payment.transaction_reference,
        "paid_at": payment.paid_at,
        "created_at": payment.created_at,
    }


# ==============================================
# MARK PAYMENT PAID (COMPATIBILITY)
# ==============================================

async def mark_payment_paid(
    *,
    payment_id: int,
    session: AsyncSession,
) -> None:
    """
    تعيين الدفع كمدفوع (دالة متوافقة مع الإصدار القديم).
    
    Args:
        payment_id: معرف الدفع
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = OrderPaymentsRepository(session=session)

    await repo.mark_paid(payment_id=payment_id)

    logger.info(
        "order_payment_paid",
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
    repo = OrderPaymentsRepository(session=session)

    await repo.mark_failed(payment_id=payment_id)

    logger.info(
        "order_payment_failed",
        extra={"payment_id": payment_id},
    )


# ==============================================
# MARK PAYMENT CANCELLED (COMPATIBILITY)
# ==============================================

async def mark_payment_cancelled(
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
    repo = OrderPaymentsRepository(session=session)

    await repo.mark_cancelled(payment_id=payment_id)

    logger.info(
        "order_payment_cancelled",
        extra={"payment_id": payment_id},
    )


# ==============================================
# DELETE ORDER PAYMENT (COMPATIBILITY)
# ==============================================

async def delete_order_payment(
    *,
    payment_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف دفع (دالة متوافقة مع الإصدار القديم).
    
    Args:
        payment_id: معرف الدفع
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = OrderPaymentsRepository(session=session)

    await repo.delete(id=payment_id)

    logger.info(
        "order_payment_deleted",
        extra={"payment_id": payment_id},
    )