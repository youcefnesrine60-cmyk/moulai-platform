# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / PAYMENT SERVICE
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for payment service.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from typing import (
    Any,
    TypeAlias,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

# ✅ استيراد دوال الأمان
from app.core.logger import logger
from app.models.payment import Payment
from app.models.restaurant import Restaurant
from app.repositories.payment_repo import PaymentRepository
from app.repositories.subscription_repo import SubscriptionRepository

# ✅ استيراد المخططات
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
    PaymentStatusUpdate,
    PaymentSummary,
)
from app.services.business.payment_providers import get_payment_provider
from app.services.business.payment_transaction import payment_transaction
from app.services.business.subscription_service import SubscriptionService

# ==============================================
# 🧩 CONSTANTS
# ==============================================

VALID_PAYMENT_STATUSES = {"pending", "paid", "failed", "cancelled", "refunded"}
ALLOWED_PAYMENT_METHODS = {"cash", "card", "ccp", "baridimob", "stripe", "paypal"}


# ==============================================
# 🧩 TYPES
# ==============================================

PaymentResult: TypeAlias = dict[str, Any]
PaymentList: TypeAlias = list[Payment]


# ==============================================
# 💳 PAYMENT SERVICE
# ==============================================


class PaymentService:
    """
    خدمة المدفوعات - تدير منطق الأعمال للمدفوعات.

    مسؤولة عن:
        - إنشاء طلبات الدفع
        - تأكيد الدفع
        - فشل الدفع
        - إلغاء الدفع
        - التحقق من حالة الدفع
        - منع الدفع المكرر

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع المدفوعات
        subscription_repo: مستودع الاشتراكات
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        *,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة المدفوعات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = PaymentRepository(session=session)
        self.subscription_repo = SubscriptionRepository(session=session)
        # Payment response schemas use scalar columns, not relationship graphs.
        self.repo.query_options = [raiseload("*")]
        self.subscription_repo.query_options = [raiseload("*")]

    # ==============================================
    # CONFIRM AUTHENTICATED PROVIDER PAYMENT
    # ==============================================

    async def confirm_external_payment(self, *, external_reference: str) -> None:
        """Settle a payment from an authenticated provider event in one transaction."""

        async with payment_transaction(session=self.session):
            payment = await self.repo.get_by_external_reference(
                external_reference=external_reference, for_update=True
            )
            if payment is None:
                raise ValueError("payment_not_found")
            if not payment.subscription_id:
                raise ValueError("subscription_not_found")
            await self.confirm_payment(payment_id=payment.id)

    # ==============================================
    # RECORD AUTHENTICATED PROVIDER FAILURE
    # ==============================================

    async def fail_external_payment(self, *, external_reference: str) -> None:
        """Record a gateway failure without downgrading a terminal payment."""

        async with payment_transaction(session=self.session):
            payment = await self.repo.get_by_external_reference(
                external_reference=external_reference,
                for_update=True,
            )
            if payment is None:
                raise ValueError("payment_not_found")
            if payment.status in {"paid", "failed", "cancelled", "refunded"}:
                return
            await self._validate_status_transition(
                current_status=payment.status,
                new_status="failed",
            )
            if await self.repo.mark_failed(payment_id=payment.id) is None:
                raise ValueError("payment_not_found")
        logger.warning("payment_callback_failed", extra={"payment_id": payment.id})

    # ==========================================
    # 🛠️ PRIVATE HELPERS
    # ==========================================

    # ==============================================
    # VALIDATE PAYMENT STATUS TRANSITION
    # ==============================================

    async def _validate_status_transition(
        self,
        *,
        current_status: str,
        new_status: str,
    ) -> None:
        """
        التحقق من صحة انتقال حالة الدفع.

        Args:
            current_status: الحالة الحالية
            new_status: الحالة الجديدة

        Raises:
            ValidationError: إذا كان الانتقال غير صالح
        """
        # التحقق من صحة الحالات
        if current_status not in VALID_PAYMENT_STATUSES:
            raise ValidationError(
                message=f"حالة الدفع '{current_status}' غير صالحة",
            )

        if new_status not in VALID_PAYMENT_STATUSES:
            raise ValidationError(
                message=f"حالة الدفع '{new_status}' غير صالحة",
            )

        # تعريف انتقالات الحالات الصالحة
        valid_transitions: dict[str, set] = {
            "pending": {"paid", "failed", "cancelled"},
            "paid": {"refunded"},
            "failed": set(),
            "cancelled": set(),
            "refunded": set(),
        }

        if new_status not in valid_transitions.get(current_status, set()):
            raise ValidationError(
                message=f"لا يمكن الانتقال من حالة '{current_status}' إلى '{new_status}'",
                details={
                    "current_status": current_status,
                    "new_status": new_status,
                    "allowed_transitions": list(
                        valid_transitions.get(current_status, set())
                    ),
                },
            )

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        payment_id: int,
    ) -> PaymentResponse:
        """
        الحصول على دفع بالمعرف.

        Args:
            payment_id: معرف الدفع

        Returns:
            PaymentResponse: بيانات الدفع

        Raises:
            NotFoundError: إذا لم يتم العثور على الدفع
        """
        logger.info(
            "payment_service_get_by_id",
            extra={"payment_id": payment_id},
        )

        payment = await self.repo.get_by_id(
            id=payment_id,
        )

        if not payment:
            raise NotFoundError(
                message=f"الدفع بـ ID '{payment_id}' غير موجود",
            )

        return PaymentResponse.model_validate(payment)

    # ==============================================
    # GET BY EXTERNAL REFERENCE
    # ==============================================

    async def get_by_external_reference(
        self,
        *,
        external_reference: str,
    ) -> PaymentResponse | None:
        """
        الحصول على دفع بواسطة المرجع الخارجي.

        Args:
            external_reference: المرجع الخارجي من بوابة الدفع

        Returns:
            Optional[PaymentResponse]: بيانات الدفع أو None
        """
        logger.info(
            "payment_service_get_by_reference",
            extra={"external_reference": external_reference},
        )

        payment = await self.repo.get_by_external_reference(
            external_reference=external_reference,
        )

        if not payment:
            return None

        return PaymentResponse.model_validate(payment)

    # ==============================================
    # GET BY SUBSCRIPTION
    # ==============================================

    async def get_by_subscription(
        self,
        *,
        subscription_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PaymentResponse]:
        """
        الحصول على مدفوعات اشتراك معين.

        Args:
            subscription_id: معرف الاشتراك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            List[PaymentResponse]: قائمة المدفوعات
        """
        logger.info(
            "payment_service_get_by_subscription",
            extra={
                "subscription_id": subscription_id,
                "skip": skip,
                "limit": limit,
            },
        )

        payments = await self.repo.get_by_subscription_id(
            subscription_id=subscription_id,
            skip=skip,
            limit=limit,
        )

        return [PaymentResponse.model_validate(payment) for payment in payments]

    # ==============================================
    # GET BY STATUS
    # ==============================================

    async def get_by_status(
        self,
        *,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PaymentResponse]:
        """
        الحصول على مدفوعات حسب الحالة.

        Args:
            status: حالة الدفع (pending, paid, failed, cancelled)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            List[PaymentResponse]: قائمة المدفوعات

        Raises:
            ValidationError: إذا كانت الحالة غير صالحة
        """
        if status not in VALID_PAYMENT_STATUSES:
            raise ValidationError(
                message=f"حالة الدفع '{status}' غير صالحة",
                details={
                    "status": status,
                    "valid_statuses": list(VALID_PAYMENT_STATUSES),
                },
            )

        logger.info(
            "payment_service_get_by_status",
            extra={
                "status": status,
                "skip": skip,
                "limit": limit,
            },
        )

        payments = await self.repo.get_by_status(
            status=status,
            skip=skip,
            limit=limit,
        )

        return [PaymentResponse.model_validate(payment) for payment in payments]

    # ==============================================
    # GET PAYMENT SUMMARY
    # ==============================================

    async def get_payment_summary(
        self,
        *,
        restaurant_id: int | None = None,
        owner_id: int | None = None,
    ) -> PaymentSummary:
        """
        الحصول على ملخص المدفوعات.

        Args:
            restaurant_id: معرف المطعم (اختياري)
            owner_id: معرف المالك (اختياري)

        Returns:
            PaymentSummary: ملخص المدفوعات
        """
        logger.info(
            "payment_service_get_payment_summary",
            extra={
                "restaurant_id": restaurant_id,
                "owner_id": owner_id,
            },
        )

        # بناء الفلاتر
        filters = {}

        if restaurant_id:
            filters["restaurant_id"] = restaurant_id

        if owner_id:
            filters["owner_id"] = owner_id

        # الحصول على جميع المدفوعات
        payments = await self.repo.get_all(
            filters=filters,
            limit=10000,
        )

        total_payments = len(payments)
        total_amount = 0.0
        paid_amount = 0.0
        pending_amount = 0.0

        status_counts: dict[str, int] = {}

        for payment in payments:
            total_amount += payment.amount

            if payment.status == "paid":
                paid_amount += payment.amount
            elif payment.status == "pending":
                pending_amount += payment.amount

            status_counts[payment.status] = status_counts.get(payment.status, 0) + 1

        return PaymentSummary(
            total_payments=total_payments,
            total_amount=total_amount,
            paid_amount=paid_amount,
            pending_amount=pending_amount,
            status_counts=status_counts,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE PAYMENT
    # ==============================================

    async def create_payment(self, *, payment_data: PaymentCreate) -> PaymentResponse:
        """Create a manual subscription invoice from the server's stored price."""
        provider = get_payment_provider(method=payment_data.payment_method)
        if (
            not payment_data.subscription_id
            or payment_data.external_reference is not None
        ):
            raise ValidationError(
                message="A pending subscription is required; submit its reference with receipt evidence"
            )
        async with payment_transaction(session=self.session):
            subscription = await self.subscription_repo.get_by_id_for_update(
                subscription_id=payment_data.subscription_id
            )
            if subscription is None:
                raise NotFoundError(message="Subscription not found")
            if (
                subscription.owner_id != payment_data.owner_id
                or subscription.restaurant_id != payment_data.restaurant_id
            ):
                raise NotFoundError(message="Subscription not found")
            restaurant_owner = (
                await self.session.execute(
                    select(Restaurant.owner_id).where(
                        Restaurant.id == payment_data.restaurant_id
                    )
                )
            ).scalar_one_or_none()
            if restaurant_owner != payment_data.owner_id:
                raise NotFoundError(message="Restaurant not found")
            if subscription.status not in {"pending", "pending_payment"}:
                raise ValidationError(message="Subscription is not pending payment")
            amount = Decimal(str(subscription.amount))
            provider.prepare_payment(
                method=payment_data.payment_method, amount=amount, currency="DZD"
            )
            if Decimal(str(payment_data.amount)) != amount:
                raise ValidationError(
                    message="Payment amount must match the stored subscription price"
                )
            existing = await self.repo.get_by_subscription_id(
                subscription_id=subscription.id
            )
            if any(p.status in {"pending", "paid"} for p in existing):
                raise ConflictError(
                    message="Subscription already has a pending or paid invoice"
                )
            payment = await self.repo.create(
                data={
                    "owner_id": subscription.owner_id,
                    "restaurant_id": subscription.restaurant_id,
                    "subscription_id": subscription.id,
                    "payment_method": payment_data.payment_method,
                    "payment_provider": provider.code,
                    "currency": "DZD",
                    "amount": float(amount),
                    "status": "pending",
                    "external_reference": None,
                }
            )
            result = PaymentResponse.model_validate(payment)
        return result

    # ==============================================
    # UPDATE PAYMENT STATUS
    # ==============================================

    async def update_payment_status(
        self,
        *,
        payment_id: int,
        status_data: PaymentStatusUpdate,
    ) -> PaymentResponse:
        """
        تحديث حالة الدفع.

        Args:
            payment_id: معرف الدفع
            status_data: بيانات تحديث الحالة

        Returns:
            PaymentResponse: بيانات الدفع المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الدفع
            ValidationError: إذا كان الانتقال غير صالح
        """
        logger.info(
            "payment_service_update_status",
            extra={
                "payment_id": payment_id,
                "new_status": status_data.status,
            },
        )

        payment = await self.repo.get_by_id(id=payment_id)

        if not payment:
            raise NotFoundError(
                message=f"الدفع بـ ID '{payment_id}' غير موجود",
            )

        # التحقق من صحة انتقال الحالة
        await self._validate_status_transition(
            current_status=payment.status,
            new_status=status_data.status,
        )

        # تحديث الحالة
        updated = await self.repo.update(
            id=payment_id,
            data={"status": status_data.status},
        )

        if not updated:
            raise NotFoundError(
                message=f"الدفع بـ ID '{payment_id}' غير موجود",
            )

        logger.info(
            "payment_status_updated_successfully",
            extra={
                "payment_id": payment_id,
                "old_status": payment.status,
                "new_status": status_data.status,
            },
        )

        return PaymentResponse.model_validate(updated)

    # ==============================================
    # CONFIRM PAYMENT
    # ==============================================

    async def confirm_payment(self, *, payment_id: int) -> PaymentResponse:
        """Internal settlement command; API callers must supply verified authority."""
        async with payment_transaction(session=self.session):
            payment = (
                await self.session.execute(
                    select(Payment)
                    .options(raiseload("*"))
                    .where(Payment.id == payment_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            ).scalar_one_or_none()
            if payment is None:
                raise NotFoundError(message="Payment not found")
            if payment.status == "paid":
                return PaymentResponse.model_validate(payment)
            await self._validate_status_transition(
                current_status=payment.status, new_status="paid"
            )
            updated = await self.repo.mark_paid(
                payment_id=payment_id,
                paid_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            if updated is None:
                raise NotFoundError(message="Payment not found")
            await SubscriptionService(
                session=self.session
            ).activate_for_verified_payment(payment=updated)
            result = PaymentResponse.model_validate(updated)
        return result

    # ==============================================
    # FAIL PAYMENT
    # ==============================================

    async def fail_payment(
        self,
        *,
        payment_id: int,
    ) -> PaymentResponse:
        """
        تعيين الدفع كفاشل.

        Args:
            payment_id: معرف الدفع

        Returns:
            PaymentResponse: بيانات الدفع المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الدفع
            ValidationError: إذا كانت الحالة غير صالحة للانتقال
        """
        logger.info(
            "payment_service_fail",
            extra={"payment_id": payment_id},
        )

        payment = await self.repo.get_by_id(id=payment_id)

        if not payment:
            raise NotFoundError(
                message=f"الدفع بـ ID '{payment_id}' غير موجود",
            )

        # التحقق من صحة الانتقال
        await self._validate_status_transition(
            current_status=payment.status,
            new_status="failed",
        )

        updated = await self.repo.mark_failed(payment_id=payment_id)

        if not updated:
            raise NotFoundError(
                message=f"الدفع بـ ID '{payment_id}' غير موجود",
            )

        logger.info(
            "payment_failed",
            extra={"payment_id": payment_id},
        )

        return PaymentResponse.model_validate(updated)

    # ==============================================
    # CANCEL PAYMENT
    # ==============================================

    async def cancel_payment(
        self,
        *,
        payment_id: int,
    ) -> PaymentResponse:
        """
        إلغاء الدفع.

        Args:
            payment_id: معرف الدفع

        Returns:
            PaymentResponse: بيانات الدفع المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الدفع
            ValidationError: إذا كانت الحالة غير صالحة للانتقال
        """
        logger.info(
            "payment_service_cancel",
            extra={"payment_id": payment_id},
        )

        payment = await self.repo.get_by_id(id=payment_id)

        if not payment:
            raise NotFoundError(
                message=f"الدفع بـ ID '{payment_id}' غير موجود",
            )

        # التحقق من صحة الانتقال
        await self._validate_status_transition(
            current_status=payment.status,
            new_status="cancelled",
        )

        updated = await self.repo.mark_cancelled(payment_id=payment_id)

        if not updated:
            raise NotFoundError(
                message=f"الدفع بـ ID '{payment_id}' غير موجود",
            )

        logger.info(
            "payment_cancelled",
            extra={"payment_id": payment_id},
        )

        return PaymentResponse.model_validate(updated)

    # ==============================================
    # REFUND PAYMENT
    # ==============================================

    async def refund_payment(
        self,
        *,
        payment_id: int,
    ) -> PaymentResponse:
        """
        استرداد الدفع.

        Args:
            payment_id: معرف الدفع

        Returns:
            PaymentResponse: بيانات الدفع المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الدفع
            ValidationError: إذا كانت الحالة غير صالحة للانتقال
        """
        logger.info(
            "payment_service_refund",
            extra={"payment_id": payment_id},
        )

        payment = await self.repo.get_by_id(id=payment_id)

        if not payment:
            raise NotFoundError(
                message=f"الدفع بـ ID '{payment_id}' غير موجود",
            )

        # التحقق من صحة الانتقال
        await self._validate_status_transition(
            current_status=payment.status,
            new_status="refunded",
        )

        updated = await self.repo.update(
            id=payment_id,
            data={"status": "refunded"},
        )

        if not updated:
            raise NotFoundError(
                message=f"الدفع بـ ID '{payment_id}' غير موجود",
            )

        logger.info(
            "payment_refunded",
            extra={"payment_id": payment_id},
        )

        return PaymentResponse.model_validate(updated)

    # ==============================================
    # DELETE PAYMENT
    # ==============================================

    async def delete_payment(
        self,
        *,
        payment_id: int,
    ) -> None:
        """
        حذف دفع.

        Args:
            payment_id: معرف الدفع

        Raises:
            NotFoundError: إذا لم يتم العثور على الدفع
            ValidationError: إذا كان الدفع مدفوعاً أو معلقاً
        """
        logger.info(
            "payment_service_delete",
            extra={"payment_id": payment_id},
        )

        payment = await self.repo.get_by_id(id=payment_id)

        if not payment:
            raise NotFoundError(
                message=f"الدفع بـ ID '{payment_id}' غير موجود",
            )

        # لا يمكن حذف دفع مدفوع أو معلق
        if payment.status in ["paid", "pending"]:
            raise ValidationError(
                message=f"لا يمكن حذف دفع بحالة '{payment.status}'",
                details={
                    "payment_id": payment_id,
                    "payment_status": payment.status,
                },
            )

        await self.repo.delete(id=payment_id)

        logger.info(
            "payment_deleted_successfully",
            extra={"payment_id": payment_id},
        )
