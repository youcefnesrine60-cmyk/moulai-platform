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

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

# ✅ استيراد دوال الأمان

from app.core.logger import logger
from app.models.payment import Payment
from app.repositories.payment_repo import PaymentRepository
from app.repositories.subscription_repo import SubscriptionRepository

# ✅ استيراد المخططات
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
    PaymentStatusUpdate,
    PaymentSummary,
)

# ==============================================
# 🧩 CONSTANTS
# ==============================================

VALID_PAYMENT_STATUSES = {"pending", "paid", "failed", "cancelled", "refunded"}
ALLOWED_PAYMENT_METHODS = {"cash", "card", "ccp", "baridimob", "stripe", "paypal"}


# ==============================================
# 🧩 TYPES
# ==============================================

PaymentResult = Dict[str, Any]
PaymentList = List[Payment]


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
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة المدفوعات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = PaymentRepository(session)
        self.subscription_repo = SubscriptionRepository(session)

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
        valid_transitions: Dict[str, set] = {
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
    ) -> Optional[PaymentResponse]:
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
    ) -> List[PaymentResponse]:
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
    ) -> List[PaymentResponse]:
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
        restaurant_id: Optional[int] = None,
        owner_id: Optional[int] = None,
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

        status_counts: Dict[str, int] = {}

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

    async def create_payment(
        self,
        *,
        payment_data: PaymentCreate,
    ) -> PaymentResponse:
        """
        إنشاء طلب دفع جديد.

        Args:
            payment_data: بيانات الدفع

        Returns:
            PaymentResponse: بيانات الدفع المنشأ

        Raises:
            NotFoundError: إذا لم يتم العثور على الاشتراك
            ConflictError: إذا كان هناك دفع معلق أو مدفوع لنفس الاشتراك
            ValidationError: إذا كانت البيانات غير صالحة
        """
        logger.info(
            "payment_service_create",
            extra={
                "owner_id": payment_data.owner_id,
                "restaurant_id": payment_data.restaurant_id,
                "subscription_id": payment_data.subscription_id,
                "amount": payment_data.amount,
            },
        )

        # التحقق من صحة المبلغ
        if payment_data.amount <= 0:
            raise ValidationError(
                message="مبلغ الدفع يجب أن يكون أكبر من الصفر",
            )

        # التحقق من صحة طريقة الدفع
        if payment_data.payment_method not in ALLOWED_PAYMENT_METHODS:
            raise ValidationError(
                message=f"طريقة الدفع '{payment_data.payment_method}' غير مدعومة",
                details={
                    "payment_method": payment_data.payment_method,
                    "allowed_methods": list(ALLOWED_PAYMENT_METHODS),
                },
            )

        # التحقق من وجود الاشتراك
        if payment_data.subscription_id:
            subscription = await self.subscription_repo.get_by_id(
                id=payment_data.subscription_id,
            )

            if not subscription:
                raise NotFoundError(
                    message=f"الاشتراك بـ ID '{payment_data.subscription_id}' غير موجود",
                )

        # التحقق من عدم وجود دفع معلق أو مدفوع لنفس الاشتراك
        existing_payments = await self.repo.get_by_subscription_id(
            subscription_id=payment_data.subscription_id,
        )

        for payment in existing_payments:
            if payment.status in ["pending", "paid"]:
                raise ConflictError(
                    message=f"يوجد بالفعل دفع {payment.status} لهذا الاشتراك",
                    details={
                        "subscription_id": payment_data.subscription_id,
                        "existing_payment_id": payment.id,
                        "existing_status": payment.status,
                    },
                )

        # إنشاء الدفع
        data: Dict[str, Any] = {
            "owner_id": payment_data.owner_id,
            "restaurant_id": payment_data.restaurant_id,
            "subscription_id": payment_data.subscription_id,
            "payment_method": payment_data.payment_method,
            "amount": payment_data.amount,
            "status": "pending",
            "external_reference": payment_data.external_reference,
        }

        payment = await self.repo.create(data=data)

        logger.info(
            "payment_request_created",
            extra={
                "payment_id": payment.id,
                "restaurant_id": payment_data.restaurant_id,
                "amount": payment_data.amount,
            },
        )

        return PaymentResponse.model_validate(payment)

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

    async def confirm_payment(
        self,
        *,
        payment_id: int,
    ) -> PaymentResponse:
        """
        تأكيد الدفع (تعيين الحالة إلى paid).

        Args:
            payment_id: معرف الدفع

        Returns:
            PaymentResponse: بيانات الدفع المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الدفع
            ValidationError: إذا كانت الحالة غير صالحة للانتقال
        """
        logger.info(
            "payment_service_confirm",
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
            new_status="paid",
        )

        # تأكيد الدفع
        updated = await self.repo.mark_paid(payment_id=payment_id)

        if not updated:
            raise NotFoundError(
                message=f"الدفع بـ ID '{payment_id}' غير موجود",
            )

        logger.info(
            "payment_confirmed",
            extra={"payment_id": payment_id},
        )

        return PaymentResponse.model_validate(updated)

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


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE PAYMENT REQUEST (COMPATIBILITY)
# ==============================================


async def create_payment_request(
    *,
    owner_id: int,
    restaurant_id: int,
    subscription_id: Optional[int],
    payment_method: str,
    amount: float,
    external_reference: Optional[str] = None,
    session: AsyncSession,
) -> int:
    """
    إنشاء طلب دفع جديد (دالة متوافقة مع الإصدار القديم).

    Args:
        owner_id: معرف المالك
        restaurant_id: معرف المطعم
        subscription_id: معرف الاشتراك
        payment_method: طريقة الدفع
        amount: المبلغ
        external_reference: المرجع الخارجي
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        int: معرف الدفع

    Raises:
        NotFoundError: إذا لم يتم العثور على الاشتراك
        ConflictError: إذا كان هناك دفع معلق أو مدفوع
        ValidationError: إذا كانت البيانات غير صالحة
    """
    service = PaymentService(session=session)

    payment_data = PaymentCreate(
        owner_id=owner_id,
        restaurant_id=restaurant_id,
        subscription_id=subscription_id,
        payment_method=payment_method,
        amount=amount,
        external_reference=external_reference,
    )

    payment = await service.create_payment(
        payment_data=payment_data,
    )

    return payment.id


# ==============================================
# GET PAYMENT (COMPATIBILITY)
# ==============================================


async def get_payment(
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
        Optional[Dict[str, Any]]: قاموس بيانات الدفع أو None
    """
    service = PaymentService(session=session)

    try:
        payment = await service.get_by_id(payment_id=payment_id)
        return payment.model_dump()
    except NotFoundError:
        return None


# ==============================================
# GET PAYMENT BY EXTERNAL REFERENCE (COMPATIBILITY)
# ==============================================


async def get_payment_by_external_reference(
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
        Optional[Dict[str, Any]]: قاموس بيانات الدفع أو None
    """
    service = PaymentService(session=session)

    payment = await service.get_by_external_reference(
        external_reference=external_reference,
    )

    if not payment:
        return None

    return payment.model_dump()


# ==============================================
# CONFIRM PAYMENT (COMPATIBILITY)
# ==============================================


async def confirm_payment(
    *,
    payment_id: int,
    session: AsyncSession,
) -> None:
    """
    تأكيد الدفع (دالة متوافقة مع الإصدار القديم).

    Args:
        payment_id: معرف الدفع
        session: جلسة قاعدة البيانات غير المتزامنة

    Raises:
        NotFoundError: إذا لم يتم العثور على الدفع
        ValidationError: إذا كانت الحالة غير صالحة للانتقال
    """
    service = PaymentService(session=session)

    await service.confirm_payment(payment_id=payment_id)

    logger.info(
        "payment_confirmed",
        extra={"payment_id": payment_id},
    )


# ==============================================
# FAIL PAYMENT (COMPATIBILITY)
# ==============================================


async def fail_payment(
    *,
    payment_id: int,
    session: AsyncSession,
) -> None:
    """
    تعيين الدفع كفاشل (دالة متوافقة مع الإصدار القديم).

    Args:
        payment_id: معرف الدفع
        session: جلسة قاعدة البيانات غير المتزامنة

    Raises:
        NotFoundError: إذا لم يتم العثور على الدفع
        ValidationError: إذا كانت الحالة غير صالحة للانتقال
    """
    service = PaymentService(session=session)

    await service.fail_payment(payment_id=payment_id)

    logger.info(
        "payment_failed",
        extra={"payment_id": payment_id},
    )


# ==============================================
# CANCEL PAYMENT REQUEST (COMPATIBILITY)
# ==============================================


async def cancel_payment_request(
    *,
    payment_id: int,
    session: AsyncSession,
) -> None:
    """
    إلغاء الدفع (دالة متوافقة مع الإصدار القديم).

    Args:
        payment_id: معرف الدفع
        session: جلسة قاعدة البيانات غير المتزامنة

    Raises:
        NotFoundError: إذا لم يتم العثور على الدفع
        ValidationError: إذا كانت الحالة غير صالحة للانتقال
    """
    service = PaymentService(session=session)

    await service.cancel_payment(payment_id=payment_id)

    logger.info(
        "payment_cancelled",
        extra={"payment_id": payment_id},
    )


# ==============================================
# REFUND PAYMENT (COMPATIBILITY)
# ==============================================


async def refund_payment(
    *,
    payment_id: int,
    session: AsyncSession,
) -> None:
    """
    استرداد الدفع (دالة متوافقة مع الإصدار القديم).

    Args:
        payment_id: معرف الدفع
        session: جلسة قاعدة البيانات غير المتزامنة

    Raises:
        NotFoundError: إذا لم يتم العثور على الدفع
        ValidationError: إذا كانت الحالة غير صالحة للانتقال
    """
    service = PaymentService(session=session)

    await service.refund_payment(payment_id=payment_id)

    logger.info(
        "payment_refunded",
        extra={"payment_id": payment_id},
    )


# ==============================================
# IS PAYMENT PAID (COMPATIBILITY)
# ==============================================


async def is_payment_paid(
    *,
    payment_id: int,
    session: AsyncSession,
) -> bool:
    """
    التحقق من أن الدفع مدفوع (دالة متوافقة مع الإصدار القديم).

    Args:
        payment_id: معرف الدفع
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        bool: True إذا كان مدفوعاً
    """
    service = PaymentService(session=session)

    return await service.is_payment_paid(payment_id=payment_id)


# ==============================================
# IS PAYMENT PENDING (COMPATIBILITY)
# ==============================================


async def is_payment_pending(
    *,
    payment_id: int,
    session: AsyncSession,
) -> bool:
    """
    التحقق من أن الدفع معلق (دالة متوافقة مع الإصدار القديم).

    Args:
        payment_id: معرف الدفع
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        bool: True إذا كان معلقاً
    """
    service = PaymentService(session=session)

    return await service.is_payment_pending(payment_id=payment_id)
