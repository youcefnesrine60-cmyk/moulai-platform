# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / EXCEPTIONS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for exceptions.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
    Dict,
    Optional,
)

# ==============================================
# 📦 BASE EXCEPTION
# ==============================================


class AppException(Exception):
    """
    الاستثناء الأساسي لجميع استثناءات التطبيق.

    Attributes:
        message: رسالة الخطأ
        status_code: رمز حالة HTTP
        details: تفاصيل إضافية عن الخطأ
        error_code: رمز الخطأ المخصص
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "حدث خطأ في التطبيق",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.error_code = error_code
        super().__init__(message)


# ==============================================
# 🔍 NOT FOUND EXCEPTIONS
# ==============================================


class NotFoundError(AppException):
    """استثناء عند عدم العثور على المورد."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "المورد غير موجود",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = "NOT_FOUND",
    ) -> None:
        super().__init__(
            message=message,
            status_code=404,
            details=details,
            error_code=error_code,
        )


class RestaurantNotFoundError(NotFoundError):
    """استثناء عند عدم العثور على مطعم."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        restaurant_id: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = (
            message
            or f"المطعم {f'بـ ID {restaurant_id}' if restaurant_id else ''} غير موجود"
        )
        super().__init__(
            message=msg,
            details={"restaurant_id": restaurant_id} if restaurant_id else None,
            error_code="RESTAURANT_NOT_FOUND",
        )


class AdminNotFoundError(NotFoundError):
    """استثناء عند عدم العثور على مدير."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        admin_id: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = message or f"المدير {f'بـ ID {admin_id}' if admin_id else ''} غير موجود"
        super().__init__(
            message=msg,
            details={"admin_id": admin_id} if admin_id else None,
            error_code="ADMIN_NOT_FOUND",
        )


class BranchNotFoundError(NotFoundError):
    """استثناء عند عدم العثور على فرع."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        branch_id: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = message or f"الفرع {f'بـ ID {branch_id}' if branch_id else ''} غير موجود"
        super().__init__(
            message=msg,
            details={"branch_id": branch_id} if branch_id else None,
            error_code="BRANCH_NOT_FOUND",
        )


class ProductNotFoundError(NotFoundError):
    """استثناء عند عدم العثور على منتج."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        product_id: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = (
            message or f"المنتج {f'بـ ID {product_id}' if product_id else ''} غير موجود"
        )
        super().__init__(
            message=msg,
            details={"product_id": product_id} if product_id else None,
            error_code="PRODUCT_NOT_FOUND",
        )


class OrderNotFoundError(NotFoundError):
    """استثناء عند عدم العثور على طلب."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        order_id: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = message or f"الطلب {f'بـ ID {order_id}' if order_id else ''} غير موجود"
        super().__init__(
            message=msg,
            details={"order_id": order_id} if order_id else None,
            error_code="ORDER_NOT_FOUND",
        )


class UserNotFoundError(NotFoundError):
    """استثناء عند عدم العثور على مستخدم."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        user_id: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = message or f"المستخدم {f'بـ ID {user_id}' if user_id else ''} غير موجود"
        super().__init__(
            message=msg,
            details={"user_id": user_id} if user_id else None,
            error_code="USER_NOT_FOUND",
        )


# ==============================================
# ⚔️ CONFLICT EXCEPTIONS
# ==============================================


class ConflictError(AppException):
    """استثناء عند وجود تعارض في البيانات."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "تعارض في البيانات",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = "CONFLICT",
    ) -> None:
        super().__init__(
            message=message,
            status_code=409,
            details=details,
            error_code=error_code,
        )


class DuplicateUsernameError(ConflictError):
    """استثناء عند وجود اسم مستخدم مكرر."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        username: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = message or f"اسم المستخدم '{username}' موجود مسبقاً"
        super().__init__(
            message=msg,
            details={"username": username} if username else None,
            error_code="DUPLICATE_USERNAME",
        )


class DuplicateEmailError(ConflictError):
    """استثناء عند وجود بريد إلكتروني مكرر."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        email: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = message or f"البريد الإلكتروني '{email}' موجود مسبقاً"
        super().__init__(
            message=msg,
            details={"email": email} if email else None,
            error_code="DUPLICATE_EMAIL",
        )


class DuplicateChatIdError(ConflictError):
    """استثناء عند وجود chat_id مكرر."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        chat_id: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = message or f"المستخدم بـ chat_id '{chat_id}' موجود مسبقاً"
        super().__init__(
            message=msg,
            details={"chat_id": chat_id} if chat_id else None,
            error_code="DUPLICATE_CHAT_ID",
        )


# ==============================================
# 🔐 UNAUTHORIZED EXCEPTIONS
# ==============================================


class UnauthorizedError(AppException):
    """استثناء عند عدم وجود صلاحية."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "غير مصرح به",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = "UNAUTHORIZED",
    ) -> None:
        super().__init__(
            message=message,
            status_code=401,
            details=details,
            error_code=error_code,
        )


class InvalidCredentialsError(UnauthorizedError):
    """استثناء عند عدم صحة بيانات الدخول."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "بيانات الدخول غير صحيحة",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            details=details,
            error_code="INVALID_CREDENTIALS",
        )


class InvalidSessionError(UnauthorizedError):
    """استثناء عند انتهاء صلاحية الجلسة."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "الجلسة غير صالحة أو منتهية",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            details=details,
            error_code="INVALID_SESSION",
        )


class InsufficientPermissionError(UnauthorizedError):
    """استثناء عند عدم وجود صلاحية كافية."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        required_role: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = (
            message
            or f"ليس لديك صلاحية كافية{f' (مطلوب: {required_role})' if required_role else ''}"
        )
        super().__init__(
            message=msg,
            details={"required_role": required_role} if required_role else None,
            error_code="INSUFFICIENT_PERMISSION",
        )


class AccountInactiveError(UnauthorizedError):
    """استثناء عند محاولة دخول حساب غير نشط."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "الحساب غير نشط، يرجى الاتصال بالدعم",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            details=details,
            error_code="ACCOUNT_INACTIVE",
        )


# ==============================================
# ✅ VALIDATION EXCEPTIONS
# ==============================================


class ValidationError(AppException):
    """استثناء عند فشل التحقق من صحة البيانات."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "بيانات غير صحيحة",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = "VALIDATION_ERROR",
    ) -> None:
        super().__init__(
            message=message,
            status_code=422,
            details=details,
            error_code=error_code,
        )


class InvalidInputError(ValidationError):
    """استثناء عند إدخال بيانات غير صحيحة."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = message or f"بيانات غير صحيحة{f' للحقل {field}' if field else ''}"
        super().__init__(
            message=msg,
            details={"field": field, "value": value} if field else None,
            error_code="INVALID_INPUT",
        )


class MissingRequiredFieldError(ValidationError):
    """استثناء عند فقدان حقل مطلوب."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        field: str,
        message: Optional[str] = None,
    ) -> None:
        msg = message or f"الحقل '{field}' مطلوب"
        super().__init__(
            message=msg,
            details={"field": field},
            error_code="MISSING_REQUIRED_FIELD",
        )


# ==============================================
# 🚫 FORBIDDEN EXCEPTIONS
# ==============================================


class ForbiddenError(AppException):
    """استثناء عند محاولة الوصول إلى مورد محظور."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "غير مسموح بالوصول",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = "FORBIDDEN",
    ) -> None:
        super().__init__(
            message=message,
            status_code=403,
            details=details,
            error_code=error_code,
        )


class RestaurantAccessDeniedError(ForbiddenError):
    """استثناء عند محاولة الوصول إلى مطعم غير مسموح به."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        restaurant_id: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = message or "ليس لديك صلاحية الوصول إلى هذا المطعم"
        super().__init__(
            message=msg,
            details={"restaurant_id": restaurant_id} if restaurant_id else None,
            error_code="RESTAURANT_ACCESS_DENIED",
        )


# ==============================================
# 💳 PAYMENT EXCEPTIONS
# ==============================================


class PaymentError(AppException):
    """استثناء عند فشل عملية الدفع."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "فشل في عملية الدفع",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = "PAYMENT_ERROR",
    ) -> None:
        super().__init__(
            message=message,
            status_code=402,
            details=details,
            error_code=error_code,
        )


class InsufficientBalanceError(PaymentError):
    """استثناء عند عدم كفاية الرصيد."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "الرصيد غير كافٍ لإتمام العملية",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            details=details,
            error_code="INSUFFICIENT_BALANCE",
        )


# ==============================================
# 🗄️ DATABASE EXCEPTIONS
# ==============================================


class DatabaseError(AppException):
    """استثناء عند حدوث خطأ في قاعدة البيانات."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "خطأ في قاعدة البيانات",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = "DATABASE_ERROR",
    ) -> None:
        super().__init__(
            message=message,
            status_code=500,
            details=details,
            error_code=error_code,
        )


class DuplicateEntryError(DatabaseError):
    """استثناء عند وجود إدخال مكرر في قاعدة البيانات."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = message or f"إدخال مكرر{f' في الحقل {field}' if field else ''}"
        super().__init__(
            message=msg,
            details={"field": field, "value": value} if field else None,
            error_code="DUPLICATE_ENTRY",
        )


# ==============================================
# 🤖 TELEGRAM EXCEPTIONS
# ==============================================


class TelegramAPIError(Exception):
    """
    استثناء عند حدوث خطأ في Telegram API.

    ملاحظة: هذا الاستثناء موجود مسبقاً ولا يورث من AppException
    للحفاظ على التوافق مع الكود القديم.
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "خطأ في Telegram API",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class TelegramSendMessageError(TelegramAPIError):
    """استثناء عند فشل إرسال رسالة عبر Telegram."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        chat_id: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = (
            message
            or f"فشل إرسال الرسالة{f' إلى المستخدم {chat_id}' if chat_id else ''}"
        )
        super().__init__(
            message=msg,
            details={"chat_id": chat_id} if chat_id else None,
        )


# ==============================================
# 🔄 RATE LIMIT EXCEPTIONS
# ==============================================


class RateLimitError(AppException):
    """استثناء عند تجاوز حد الطلبات."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "تجاوزت حد الطلبات المسموح بها",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = "RATE_LIMIT_EXCEEDED",
    ) -> None:
        super().__init__(
            message=message,
            status_code=429,
            details=details,
            error_code=error_code,
        )


# ==============================================
# 📦 SUBSCRIPTION EXCEPTIONS
# ==============================================


class SubscriptionError(AppException):
    """استثناء عند حدوث خطأ في الاشتراك."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        message: str = "خطأ في الاشتراك",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = "SUBSCRIPTION_ERROR",
    ) -> None:
        super().__init__(
            message=message,
            status_code=402,
            details=details,
            error_code=error_code,
        )


class SubscriptionExpiredError(SubscriptionError):
    """استثناء عند انتهاء صلاحية الاشتراك."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        restaurant_id: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = (
            message
            or f"الاشتراك منتهي الصلاحية{f' للمطعم {restaurant_id}' if restaurant_id else ''}"
        )
        super().__init__(
            message=msg,
            details={"restaurant_id": restaurant_id} if restaurant_id else None,
            error_code="SUBSCRIPTION_EXPIRED",
        )


# ==============================================
# 🏢 BRANCH EXCEPTIONS
# ==============================================


class BranchLimitExceededError(AppException):
    """استثناء عند تجاوز الحد الأقصى للفروع."""

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        restaurant_id: Optional[int] = None,
        max_branches: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        msg = (
            message
            or f"تجاوزت الحد الأقصى للفروع{f' ({max_branches})' if max_branches else ''}"
        )
        super().__init__(
            message=msg,
            status_code=400,
            details=(
                {
                    "restaurant_id": restaurant_id,
                    "max_branches": max_branches,
                }
                if restaurant_id
                else None
            ),
            error_code="BRANCH_LIMIT_EXCEEDED",
        )
