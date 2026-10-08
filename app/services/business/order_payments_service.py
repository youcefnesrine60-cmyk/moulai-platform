from app.repositories.orders_repo import lock_order
from app.services.business.orders.transaction import transactional_order
# ==============================================
# 💳 ORDER PAYMENTS SERVICE
# Business Logic Layer
# منطق الأعمال لمدفوعات الطلبات
#
# إنشاء دفعة
# تأكيد دفعة
# فشل دفعة
# إلغاء دفعة
# حذف دفعة
# التحقق من حالة الدفعة
# جلب طرق الدفع المسموح بها
# ==============================================

import math

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
)

from sqlalchemy.ext.asyncio import AsyncSession

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

# ✅ استيراد دوال الأمان
from app.core.security import (
    sanitize_input,
)

from app.core.logger import logger
from app.models.order_item import OrderPayment
from app.repositories.order_payments_repo import OrderPaymentsRepository
from app.repositories.orders_repo import OrdersRepository
from app.repositories.restaurant.restaurant_payment_settings_repo import (
    RestaurantPaymentSettingsRepository,
)

# ✅ استيراد المخططات
from app.schemas.order_payment import (
    PaymentCreate,
    PaymentResponse,
    PaymentStatusUpdate,
    PaymentSummary,
)


# ==============================================
# 🧩 CONSTANTS (DEFAULT VALUES)
# ==============================================

DEFAULT_ALLOWED_METHODS: Set[str] = {
    "cash",
    "card",
}

VALID_PAYMENT_STATUSES: Set[str] = {
    "pending",
    "paid",
    "failed",
    "cancelled",
    "refunded",
}


# ==============================================
# 🧩 TYPES
# ==============================================

PaymentData = Dict[str, Any]
PaymentList = List[OrderPayment]
AllowedMethodsSet = Set[str]


# ==============================================
# 💳 ORDER PAYMENTS SERVICE
# ==============================================


class OrderPaymentsService:
    """
    خدمة مدفوعات الطلبات - تدير منطق الأعمال لمدفوعات الطلبات.
    
    مسؤولة عن:
        - إنشاء مدفوعات الطلبات
        - تأكيد وفشل وإلغاء المدفوعات
        - التحقق من حالة المدفوعات
        - جلب طرق الدفع المسموح بها
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع مدفوعات الطلبات
        orders_repo: مستودع الطلبات
        settings_repo: مستودع إعدادات الدفع
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة مدفوعات الطلبات.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = OrderPaymentsRepository(session)
        self.orders_repo = OrdersRepository(session)
        self.settings_repo = RestaurantPaymentSettingsRepository(session)

    # ==========================================
    # 🛠️ PRIVATE HELPERS
    # ==========================================

    # ==============================================
    # GET ALLOWED PAYMENT METHODS
    # ==============================================

    async def _locked_payment(self, payment_id):
        payment = await self.repo.get_by_id(id=payment_id)
        if payment is None:
            raise NotFoundError(message="Payment not found")
        await lock_order(order_id=payment.order_id, session=self.session)
        await self.session.refresh(payment, attribute_names=["payment_status", "amount", "paid_at"])
        return payment

    async def _get_allowed_payment_methods(
        self,
        *,
        restaurant_id: int,
    ) -> AllowedMethodsSet:
        """
        جلب طرق الدفع المسموح بها لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            Set[str]: مجموعة طرق الدفع المسموح بها
        """
        settings = await self.settings_repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        # إذا لم توجد إعدادات، نستخدم القيم الافتراضية
        if not settings:
            return DEFAULT_ALLOWED_METHODS.copy()

        # بناء القائمة من إعدادات المطعم
        allowed: AllowedMethodsSet = set()

        if getattr(settings, "allow_cash", False):
            allowed.add("cash")

        if getattr(settings, "allow_card", False):
            allowed.add("card")

        if getattr(settings, "allow_ccp", False):
            allowed.add("ccp")

        if getattr(settings, "allow_baridimob", False):
            allowed.add("baridimob")

        if getattr(settings, "allow_stripe", False):
            allowed.add("stripe")

        if getattr(settings, "allow_paypal", False):
            allowed.add("paypal")

        # إذا لم توجد أي طريقة مسموحة، نعود للقيم الافتراضية
        if not allowed:
            return DEFAULT_ALLOWED_METHODS.copy()

        return allowed

    # ==============================================
    # VALIDATE PAYMENT METHOD FOR ORDER
    # ==============================================

    async def _validate_payment_method_for_order(
        self,
        *,
        order_id: int,
        payment_method: str,
    ) -> None:
        """
        التحقق من صحة طريقة الدفع لطلب معين.
        
        Args:
            order_id: معرف الطلب
            payment_method: طريقة الدفع
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
            ValidationError: إذا كانت طريقة الدفع غير مسموح بها
        """
        # جلب الطلب
        order = await self.orders_repo.get_by_id(id=order_id)

        if not order:
            raise NotFoundError(
                message=f"الطلب بـ ID '{order_id}' غير موجود",
            )

        # جلب طرق الدفع المسموح بها للمطعم
        allowed_methods = await self._get_allowed_payment_methods(
            restaurant_id=order.restaurant_id,
        )

        # التحقق من صحة طريقة الدفع
        payment_method = payment_method.lower()

        if payment_method not in allowed_methods:
            raise ValidationError(
                message=f"طريقة الدفع '{payment_method}' غير مسموح بها لهذا المطعم",
                details={
                    "order_id": order_id,
                    "payment_method": payment_method,
                    "allowed_methods": list(allowed_methods),
                },
            )

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
        التحقق من صحة انتقال حالة الدفعة.
        
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
        valid_transitions: Dict[str, Set[str]] = {
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
                    "allowed_transitions": list(valid_transitions.get(current_status, set())),
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
        الحصول على دفعة بالمعرف.
        
        Args:
            payment_id: معرف الدفعة
            
        Returns:
            PaymentResponse: بيانات الدفعة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الدفعة
        """
        logger.info(
            "order_payments_service_get_by_id",
            extra={"payment_id": payment_id},
        )

        payment = await self.repo.get_by_id(
            id=payment_id,
        )

        if not payment:
            raise NotFoundError(
                message=f"الدفعة بـ ID '{payment_id}' غير موجودة",
            )

        return PaymentResponse.model_validate(payment)

    # ==============================================
    # GET BY ORDER
    # ==============================================

    async def get_by_order(
        self,
        *,
        order_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[PaymentResponse]:
        """
        الحصول على مدفوعات طلب معين.
        
        Args:
            order_id: معرف الطلب
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[PaymentResponse]: قائمة مدفوعات الطلب
        """
        logger.info(
            "order_payments_service_get_by_order",
            extra={
                "order_id": order_id,
                "skip": skip,
                "limit": limit,
            },
        )

        payments = await self.repo.get_by_order_id(
            order_id=order_id,
            skip=skip,
            limit=limit,
        )

        return [PaymentResponse.model_validate(payment) for payment in payments]

    # ==============================================
    # GET BY TRANSACTION REFERENCE
    # ==============================================

    async def get_by_transaction_reference(
        self,
        *,
        transaction_reference: str,
    ) -> Optional[PaymentResponse]:
        """
        الحصول على دفعة بواسطة مرجع المعاملة.
        
        Args:
            transaction_reference: مرجع المعاملة
            
        Returns:
            Optional[PaymentResponse]: بيانات الدفعة أو None
        """
        logger.info(
            "order_payments_service_get_by_reference",
            extra={"transaction_reference": transaction_reference},
        )

        payment = await self.repo.get_by_transaction_reference(
            transaction_reference=transaction_reference,
        )

        if not payment:
            return None

        return PaymentResponse.model_validate(payment)

    # ==============================================
    # GET ALLOWED METHODS FOR ORDER
    # ==============================================

    async def get_allowed_methods_for_order(
        self,
        *,
        order_id: int,
    ) -> AllowedMethodsSet:
        """
        جلب طرق الدفع المسموح بها لطلب معين.
        
        Args:
            order_id: معرف الطلب
            
        Returns:
            Set[str]: مجموعة طرق الدفع المسموح بها
        """
        order = await self.orders_repo.get_by_id(id=order_id)

        if not order:
            return set()

        return await self._get_allowed_payment_methods(
            restaurant_id=order.restaurant_id,
        )

    # ==============================================
    # GET ALLOWED METHODS BY RESTAURANT
    # ==============================================

    async def get_allowed_methods_by_restaurant(
        self,
        *,
        restaurant_id: int,
    ) -> AllowedMethodsSet:
        """
        جلب طرق الدفع المسموح بها لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            Set[str]: مجموعة طرق الدفع المسموح بها
        """
        return await self._get_allowed_payment_methods(
            restaurant_id=restaurant_id,
        )

    # ==============================================
    # GET PAYMENT SUMMARY
    # ==============================================

    async def get_payment_summary(
        self,
        *,
        order_id: int,
    ) -> PaymentSummary:
        """
        الحصول على ملخص مدفوعات الطلب.
        
        Args:
            order_id: معرف الطلب
            
        Returns:
            PaymentSummary: ملخص المدفوعات
        """
        logger.info(
            "order_payments_service_get_payment_summary",
            extra={"order_id": order_id},
        )

        payments = await self.repo.get_by_order_id(
            order_id=order_id,
            limit=1000,
        )

        total_payments = len(payments)
        total_amount = 0.0
        paid_amount = 0.0
        pending_amount = 0.0

        status_counts: Dict[str, int] = {}

        for payment in payments:
            total_amount += payment.amount

            if payment.payment_status == "paid":
                paid_amount += payment.amount
            elif payment.payment_status == "pending":
                pending_amount += payment.amount

            status_counts[payment.payment_status] = status_counts.get(payment.payment_status, 0) + 1

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

    @transactional_order
    async def create_payment(
        self,
        *,
        payment_data: PaymentCreate,
    ) -> PaymentResponse:
        """
        إنشاء دفعة جديدة للطلب.
        
        Args:
            payment_data: بيانات الدفعة
            
        Returns:
            PaymentResponse: بيانات الدفعة المنشأة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
            ValidationError: إذا كانت البيانات غير صالحة
        """
        order = await lock_order(order_id=payment_data.order_id, session=self.session)
        if order is None:
            raise NotFoundError(message="Order not found")
        if order.status == "cancelled":
            raise ValidationError(message="Cannot pay a cancelled order")

        logger.info(
            "order_payments_service_create_payment",
            extra={
                "order_id": payment_data.order_id,
                "payment_method": payment_data.payment_method,
                "amount": payment_data.amount,
            },
        )

        # التحقق من صحة المبلغ
        if not math.isfinite(payment_data.amount) or payment_data.amount <= 0:
            raise ValidationError(
                message="مبلغ الدفع يجب أن يكون أكبر من الصفر",
            )

        # التحقق من صحة طريقة الدفع للطلب
        await self._validate_payment_method_for_order(
            order_id=payment_data.order_id,
            payment_method=payment_data.payment_method,
        )

        # التحقق من عدم وجود دفعة معلقة أو مدفوعة لنفس الطلب
        existing_payments = await self.repo.get_by_order_id(
            order_id=payment_data.order_id,
            limit=100,
        )

        for payment in existing_payments:
            if payment.payment_status in ["pending", "paid"]:
                raise ConflictError(
                    message=f"يوجد بالفعل دفعة {payment.payment_status} لهذا الطلب",
                    details={
                        "order_id": payment_data.order_id,
                        "existing_payment_id": payment.id,
                        "existing_status": payment.payment_status,
                    },
                )

        # إنشاء الدفعة
        data: PaymentData = {
            "order_id": payment_data.order_id,
            "payment_method": payment_data.payment_method,
            "payment_status": "pending",
            "amount": payment_data.amount,
            "transaction_reference": payment_data.transaction_reference,
        }

        payment = await self.repo.create(data=data)

        logger.info(
            "order_payment_created_successfully",
            extra={
                "payment_id": payment.id,
                "order_id": payment_data.order_id,
            },
        )

        return PaymentResponse.model_validate(payment)

    # ==============================================
    # UPDATE PAYMENT STATUS
    # ==============================================

    @transactional_order
    async def update_payment_status(
        self,
        *,
        payment_id: int,
        status_data: PaymentStatusUpdate,
    ) -> PaymentResponse:
        """
        تحديث حالة الدفعة.
        
        Args:
            payment_id: معرف الدفعة
            status_data: بيانات تحديث الحالة
            
        Returns:
            PaymentResponse: بيانات الدفعة المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الدفعة
            ValidationError: إذا كان الانتقال غير صالح
        """
        logger.info(
            "order_payments_service_update_payment_status",
            extra={
                "payment_id": payment_id,
                "new_status": status_data.payment_status,
            },
        )

        payment = await self._locked_payment(payment_id)

        if not payment:
            raise NotFoundError(
                message=f"الدفعة بـ ID '{payment_id}' غير موجودة",
            )

        # التحقق من صحة انتقال الحالة
        await self._validate_status_transition(
            current_status=payment.payment_status,
            new_status=status_data.payment_status,
        )

        # تحديث الحالة
        updated = await self.repo.update(
            id=payment_id,
            data={"payment_status": status_data.payment_status},
        )

        if not updated:
            raise NotFoundError(
                message=f"الدفعة بـ ID '{payment_id}' غير موجودة",
            )

        logger.info(
            "order_payment_status_updated_successfully",
            extra={
                "payment_id": payment_id,
                "old_status": payment.payment_status,
                "new_status": status_data.payment_status,
            },
        )

        return PaymentResponse.model_validate(updated)

    # ==============================================
    # CONFIRM PAYMENT
    # ==============================================

    @transactional_order
    async def confirm_payment(
        self,
        *,
        payment_id: int,
    ) -> PaymentResponse:
        """
        تأكيد الدفعة (تعيين الحالة إلى paid).
        
        Args:
            payment_id: معرف الدفعة
            
        Returns:
            PaymentResponse: بيانات الدفعة المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الدفعة
            ValidationError: إذا كانت الحالة غير صالحة للانتقال
        """
        logger.info(
            "order_payments_service_confirm_payment",
            extra={"payment_id": payment_id},
        )

        payment = await self._locked_payment(payment_id)

        if not payment:
            raise NotFoundError(
                message=f"الدفعة بـ ID '{payment_id}' غير موجودة",
            )

        # التحقق من صحة الانتقال
        await self._validate_status_transition(
            current_status=payment.payment_status,
            new_status="paid",
        )

        # تأكيد الدفعة
        updated = await self.repo.mark_paid(payment_id=payment_id)

        if not updated:
            raise NotFoundError(
                message=f"الدفعة بـ ID '{payment_id}' غير موجودة",
            )

        logger.info(
            "order_payment_confirmed_successfully",
            extra={"payment_id": payment_id},
        )

        return PaymentResponse.model_validate(updated)

    # ==============================================
    # FAIL PAYMENT
    # ==============================================

    @transactional_order
    async def fail_payment(
        self,
        *,
        payment_id: int,
    ) -> PaymentResponse:
        """
        تعيين الدفعة كفاشل.
        
        Args:
            payment_id: معرف الدفعة
            
        Returns:
            PaymentResponse: بيانات الدفعة المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الدفعة
            ValidationError: إذا كانت الحالة غير صالحة للانتقال
        """
        logger.info(
            "order_payments_service_fail_payment",
            extra={"payment_id": payment_id},
        )

        payment = await self._locked_payment(payment_id)

        if not payment:
            raise NotFoundError(
                message=f"الدفعة بـ ID '{payment_id}' غير موجودة",
            )

        # التحقق من صحة الانتقال
        await self._validate_status_transition(
            current_status=payment.payment_status,
            new_status="failed",
        )

        # تعيين الدفعة كفاشل
        updated = await self.repo.mark_failed(payment_id=payment_id)

        if not updated:
            raise NotFoundError(
                message=f"الدفعة بـ ID '{payment_id}' غير موجودة",
            )

        logger.info(
            "order_payment_failed_successfully",
            extra={"payment_id": payment_id},
        )

        return PaymentResponse.model_validate(updated)

    # ==============================================
    # CANCEL PAYMENT
    # ==============================================

    @transactional_order
    async def cancel_payment(
        self,
        *,
        payment_id: int,
    ) -> PaymentResponse:
        """
        إلغاء الدفعة.
        
        Args:
            payment_id: معرف الدفعة
            
        Returns:
            PaymentResponse: بيانات الدفعة المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الدفعة
            ValidationError: إذا كانت الحالة غير صالحة للانتقال
        """
        logger.info(
            "order_payments_service_cancel_payment",
            extra={"payment_id": payment_id},
        )

        payment = await self._locked_payment(payment_id)

        if not payment:
            raise NotFoundError(
                message=f"الدفعة بـ ID '{payment_id}' غير موجودة",
            )

        # التحقق من صحة الانتقال
        await self._validate_status_transition(
            current_status=payment.payment_status,
            new_status="cancelled",
        )

        # إلغاء الدفعة
        updated = await self.repo.mark_cancelled(payment_id=payment_id)

        if not updated:
            raise NotFoundError(
                message=f"الدفعة بـ ID '{payment_id}' غير موجودة",
            )

        logger.info(
            "order_payment_cancelled_successfully",
            extra={"payment_id": payment_id},
        )

        return PaymentResponse.model_validate(updated)

    # ==============================================
    # REFUND PAYMENT
    # ==============================================

    @transactional_order
    async def refund_payment(
        self,
        *,
        payment_id: int,
    ) -> PaymentResponse:
        """
        استرداد الدفعة.
        
        Args:
            payment_id: معرف الدفعة
            
        Returns:
            PaymentResponse: بيانات الدفعة المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الدفعة
            ValidationError: إذا كانت الحالة غير صالحة للانتقال
        """
        logger.info(
            "order_payments_service_refund_payment",
            extra={"payment_id": payment_id},
        )

        payment = await self._locked_payment(payment_id)

        if not payment:
            raise NotFoundError(
                message=f"الدفعة بـ ID '{payment_id}' غير موجودة",
            )

        # التحقق من صحة الانتقال
        await self._validate_status_transition(
            current_status=payment.payment_status,
            new_status="refunded",
        )

        # استرداد الدفعة
        updated = await self.repo.update(
            id=payment_id,
            data={"payment_status": "refunded"},
        )

        if not updated:
            raise NotFoundError(
                message=f"الدفعة بـ ID '{payment_id}' غير موجودة",
            )

        logger.info(
            "order_payment_refunded_successfully",
            extra={"payment_id": payment_id},
        )

        return PaymentResponse.model_validate(updated)

    # ==============================================
    # DELETE PAYMENT
    # ==============================================

    @transactional_order
    async def delete_payment(
        self,
        *,
        payment_id: int,
    ) -> None:
        """
        حذف دفعة.
        
        Args:
            payment_id: معرف الدفعة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الدفعة
            ValidationError: إذا كانت الدفعة مدفوعة أو معلقة
        """
        logger.info(
            "order_payments_service_delete_payment",
            extra={"payment_id": payment_id},
        )

        payment = await self._locked_payment(payment_id)

        if not payment:
            raise NotFoundError(
                message=f"الدفعة بـ ID '{payment_id}' غير موجودة",
            )

        # لا يمكن حذف دفعة مدفوعة أو معلقة
        if payment.payment_status in ["paid", "pending"]:
            raise ValidationError(
                message=f"لا يمكن حذف دفعة بحالة '{payment.payment_status}'",
                details={
                    "payment_id": payment_id,
                    "payment_status": payment.payment_status,
                },
            )

        await self.repo.delete(id=payment_id)

        logger.info(
            "order_payment_deleted_successfully",
            extra={"payment_id": payment_id},
        )


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE PAYMENT (COMPATIBILITY)
# ==============================================

async def create_payment(
    *,
    order_id: int,
    payment_method: str,
    amount: float,
    transaction_reference: Optional[str] = None,
    session: AsyncSession,
) -> int:
    """
    إنشاء دفعة جديدة للطلب (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        payment_method: طريقة الدفع
        amount: المبلغ
        transaction_reference: مرجع المعاملة (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        int: معرف الدفعة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
        ValidationError: إذا كانت البيانات غير صالحة
    """
    service = OrderPaymentsService(session=session)

    payment_data = PaymentCreate(
        order_id=order_id,
        payment_method=payment_method,
        amount=amount,
        transaction_reference=transaction_reference,
    )

    payment = await service.create_payment(
        payment_data=payment_data,
    )

    return payment.id


# ==============================================
# GET ALLOWED PAYMENT METHODS FOR ORDER (COMPATIBILITY)
# ==============================================

async def get_allowed_payment_methods_for_order(
    *,
    order_id: int,
    session: AsyncSession,
) -> AllowedMethodsSet:
    """
    جلب طرق الدفع المسموح بها لطلب معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Set[str]: مجموعة طرق الدفع المسموح بها
    """
    service = OrderPaymentsService(session=session)

    return await service.get_allowed_methods_for_order(order_id=order_id)


# ==============================================
# GET ALLOWED PAYMENT METHODS BY RESTAURANT (COMPATIBILITY)
# ==============================================

async def get_allowed_payment_methods_by_restaurant(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> AllowedMethodsSet:
    """
    جلب طرق الدفع المسموح بها لمطعم معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Set[str]: مجموعة طرق الدفع المسموح بها
    """
    service = OrderPaymentsService(session=session)

    return await service.get_allowed_methods_by_restaurant(
        restaurant_id=restaurant_id,
    )


# ==============================================
# CONFIRM PAYMENT (COMPATIBILITY)
# ==============================================

async def confirm_payment(
    *,
    payment_id: int,
    session: AsyncSession,
) -> None:
    """
    تأكيد دفعة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        payment_id: معرف الدفعة
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الدفعة
        ValidationError: إذا كانت الحالة غير صالحة للانتقال
    """
    service = OrderPaymentsService(session=session)

    await service.confirm_payment(payment_id=payment_id)

    logger.info(
        "order_payment_confirmed",
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
    تعيين الدفعة كفاشل (دالة متوافقة مع الإصدار القديم).
    
    Args:
        payment_id: معرف الدفعة
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الدفعة
        ValidationError: إذا كانت الحالة غير صالحة للانتقال
    """
    service = OrderPaymentsService(session=session)

    await service.fail_payment(payment_id=payment_id)

    logger.info(
        "order_payment_failed",
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
    إلغاء دفعة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        payment_id: معرف الدفعة
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الدفعة
        ValidationError: إذا كانت الحالة غير صالحة للانتقال
    """
    service = OrderPaymentsService(session=session)

    await service.cancel_payment(payment_id=payment_id)

    logger.info(
        "order_payment_cancelled",
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
    استرداد دفعة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        payment_id: معرف الدفعة
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الدفعة
        ValidationError: إذا كانت الحالة غير صالحة للانتقال
    """
    service = OrderPaymentsService(session=session)

    await service.refund_payment(payment_id=payment_id)

    logger.info(
        "order_payment_refunded",
        extra={"payment_id": payment_id},
    )


# ==============================================
# REMOVE PAYMENT (COMPATIBILITY)
# ==============================================

async def remove_payment(
    *,
    payment_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف دفعة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        payment_id: معرف الدفعة
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الدفعة
        ValidationError: إذا كانت الدفعة مدفوعة أو معلقة
    """
    service = OrderPaymentsService(session=session)

    await service.delete_payment(payment_id=payment_id)

    logger.info(
        "order_payment_removed",
        extra={"payment_id": payment_id},
    )


# ==============================================
# IS PAID (COMPATIBILITY)
# ==============================================

async def is_paid(
    *,
    payment_id: int,
    session: AsyncSession,
) -> bool:
    """
    التحقق من أن الدفعة مدفوعة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        payment_id: معرف الدفعة
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        bool: True إذا كانت مدفوعة
    """
    service = OrderPaymentsService(session=session)

    try:
        payment = await service.get_by_id(payment_id=payment_id)
        return payment.payment_status == "paid"
    except NotFoundError:
        return False


# ==============================================
# IS PENDING (COMPATIBILITY)
# ==============================================

async def is_pending(
    *,
    payment_id: int,
    session: AsyncSession,
) -> bool:
    """
    التحقق من أن الدفعة معلقة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        payment_id: معرف الدفعة
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        bool: True إذا كانت معلقة
    """
    service = OrderPaymentsService(session=session)

    try:
        payment = await service.get_by_id(payment_id=payment_id)
        return payment.payment_status == "pending"
    except NotFoundError:
        return False