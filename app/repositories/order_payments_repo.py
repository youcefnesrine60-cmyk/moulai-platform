# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / REPOSITORIES / ORDER PAYMENTS REPO
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for order payments repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

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
from datetime import datetime, timezone
from typing import (
    Any,
)

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.core.logger import logger
from app.models.order_item import OrderPayment
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

OrderPaymentData = dict[str, Any]
OrderPaymentUpdateData = dict[str, Any]
OrderPaymentList = list[OrderPayment]
OrderPaymentSummary = dict[str, Any]

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

    # ==============================================
    #   INIT
    # ==============================================

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
    ) -> OrderPayment | None:
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
        payment_status: str | None = "paid",
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
        paid_at: datetime | None = None,
    ) -> OrderPayment | None:
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
        paid_at: datetime | None = None,
    ) -> OrderPayment | None:
        """
        تعيين الدفع كمدفوع.

        Args:
            payment_id: معرف الدفع
            paid_at: تاريخ الدفع (افتراضي: الآن)

        Returns:
            كائن OrderPayment المحدث أو None
        """
        if paid_at is None:
            paid_at = datetime.now(timezone.utc).replace(tzinfo=None)

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
    ) -> OrderPayment | None:
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
    ) -> OrderPayment | None:
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
            total_cancelled = sum(
                1 for p in payments if p.payment_status == "cancelled"
            )

            total_amount = sum(p.amount for p in payments)
            total_paid_amount = sum(
                p.amount for p in payments if p.payment_status == "paid"
            )

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
