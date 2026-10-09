# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / API / V1 / PAYMENTS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for payments.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Optional,
)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Path,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import (
    OwnerPrincipal,
    get_current_owner,
    require_owned_payment,
    require_owned_restaurant,
    require_owned_subscription,
)

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

from app.core.database import get_db
from app.core.logger import logger
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
    PaymentStatus,
    PaymentSummary,
    PaymentUpdate,
    PaymentStatusUpdate,
    PaymentListResponse,
)
from app.services.business.payment_service import PaymentService
from app.services.business.subscription_service import (
    SubscriptionService,
)

# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================


async def get_payment_service(
    session: AsyncSession = Depends(get_db),
) -> PaymentService:
    """
    الحصول على خدمة المدفوعات.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        PaymentService: مثيل من PaymentService
    """
    return PaymentService(session)


# ==============================================
# GET SUBSCRIPTION SERVICE
# ==============================================


async def get_subscription_service(
    session: AsyncSession = Depends(get_db),
) -> SubscriptionService:
    """
    الحصول على خدمة الاشتراكات.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        SubscriptionService: مثيل من SubscriptionService
    """
    return SubscriptionService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# LIST PAYMENTS
# ==============================================


@router.get(
    "/",
    response_model=PaymentListResponse,
    summary="قائمة المدفوعات",
    description="الحصول على قائمة المدفوعات مع إمكانية التصفية",
)
async def list_payments(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    owner_id: Optional[int] = Query(
        None,
        description="معرف المالك",
        ge=1,
    ),
    restaurant_id: Optional[int] = Query(
        None,
        description="معرف المطعم",
        ge=1,
    ),
    status: Optional[str] = Query(
        None,
        description="حالة الدفع (pending, paid, failed, cancelled, refunded)",
        min_length=1,
        max_length=50,
    ),
    skip: int = Query(
        0,
        ge=0,
        description="عدد السجلات للتخطي",
    ),
    limit: int = Query(
        100,
        ge=1,
        le=200,
        description="الحد الأقصى للسجلات",
    ),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentListResponse:
    """
    الحصول على قائمة المدفوعات.

    Args:
        owner_id: معرف المالك للتصفية
        restaurant_id: معرف المطعم للتصفية
        status: حالة الدفع للتصفية
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة المدفوعات

    Returns:
        PaymentListResponse: قائمة المدفوعات مع الإحصائيات
    """
    if owner_id is not None and owner_id != owner.owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another owner's payments",
        )
    if restaurant_id is not None:
        await require_owned_restaurant(
            restaurant_id=restaurant_id,
            owner=owner,
            session=service.session,
        )

    logger.info(
        "api_list_payments",
        extra={
            "owner_id": owner_id,
            "restaurant_id": restaurant_id,
            "status": status,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        # تحديد طريقة الجلب بناءً على معايير التصفية
        filters = {"owner_id": owner.owner_id}
        if restaurant_id is not None:
            filters["restaurant_id"] = restaurant_id
        if status is not None:
            filters["status"] = status

        payments = await service.repo.get_all(
            skip=skip,
            limit=limit,
            filters=filters,
        )
        total = await service.repo.count(filters=filters)

        return PaymentListResponse(
            items=payments,
            total=total,
            skip=skip,
            limit=limit,
        )

    except ValidationError as e:
        logger.warning(
            "api_list_payments_validation_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_list_payments_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة المدفوعات",
        )


# ==============================================
# GET PAYMENT BY ID
# ==============================================


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="دفع بالمعرف",
    description="الحصول على دفع محدد",
)
async def get_payment(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    payment_id: int = Path(..., ge=1, description="معرف الدفع"),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """
    الحصول على دفع بالمعرف.

    Args:
        payment_id: معرف الدفع
        service: خدمة المدفوعات

    Returns:
        PaymentResponse: الدفع المطلوب

    Raises:
        HTTPException: إذا لم يتم العثور على الدفع
    """
    logger.info(
        "api_get_payment",
        extra={"payment_id": payment_id},
    )

    await require_owned_payment(
        payment_id=payment_id,
        owner=owner,
        session=service.session,
    )

    try:
        payment = await service.get_by_id(payment_id=payment_id)
        return payment

    except NotFoundError as e:
        logger.warning(
            "api_payment_not_found",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_payment_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب الدفع",
        )


# ==============================================
# GET PAYMENT STATUS
# ==============================================


@router.get(
    "/{payment_id}/status",
    response_model=PaymentStatus,
    summary="حالة الدفع",
    description="الحصول على حالة الدفع",
)
async def get_payment_status(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    payment_id: int = Path(..., ge=1, description="معرف الدفع"),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentStatus:
    """
    الحصول على حالة الدفع.

    Args:
        payment_id: معرف الدفع
        service: خدمة المدفوعات

    Returns:
        PaymentStatus: حالة الدفع

    Raises:
        HTTPException: إذا لم يتم العثور على الدفع
    """
    logger.info(
        "api_get_payment_status",
        extra={"payment_id": payment_id},
    )

    await require_owned_payment(
        payment_id=payment_id,
        owner=owner,
        session=service.session,
    )

    try:
        payment = await service.get_by_id(payment_id=payment_id)

        return PaymentStatus(
            payment_id=payment.id,
            status=payment.status,
            is_paid=payment.status == "paid",
            is_pending=payment.status == "pending",
            is_failed=payment.status == "failed",
            is_cancelled=payment.status == "cancelled",
            amount=payment.amount,
            paid_at=payment.paid_at,
        )

    except NotFoundError as e:
        logger.warning(
            "api_payment_not_found_for_status",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_payment_status_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب حالة الدفع",
        )


# ==============================================
# CREATE PAYMENT
# ==============================================


@router.post(
    "/",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء دفع",
    description="إنشاء طلب دفع جديد",
)
async def create_payment(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    data: PaymentCreate,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """
    إنشاء طلب دفع جديد.

    Args:
        data: بيانات الدفع
        service: خدمة المدفوعات

    Returns:
        PaymentResponse: الدفع المنشأ

    Raises:
        HTTPException: إذا حدث خطأ أثناء الإنشاء
    """
    logger.info(
        "api_create_payment",
        extra={
            "owner_id": data.owner_id,
            "restaurant_id": data.restaurant_id,
            "amount": data.amount,
        },
    )

    if data.owner_id != owner.owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create a payment for another owner",
        )
    await require_owned_restaurant(
        restaurant_id=data.restaurant_id,
        owner=owner,
        session=service.session,
    )
    if data.subscription_id is not None:
        await require_owned_subscription(
            subscription_id=data.subscription_id,
            owner=owner,
            session=service.session,
        )

    try:
        payment = await service.create_payment(
            payment_data=data,
        )
        return payment

    except NotFoundError as e:
        logger.warning(
            "api_create_payment_not_found",
            extra={
                "subscription_id": data.subscription_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_create_payment_conflict",
            extra={
                "subscription_id": data.subscription_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_payment_validation_error",
            extra={
                "owner_id": data.owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_payment_error",
            extra={
                "owner_id": data.owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء الدفع",
        )


# ==============================================
# UPDATE PAYMENT
# ==============================================


@router.patch(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="تحديث دفع",
    description="تحديث دفع موجود",
)
async def update_payment(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    payment_id: int = Path(..., ge=1, description="معرف الدفع"),
    data: PaymentUpdate,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """
    تحديث دفع موجود.

    Args:
        payment_id: معرف الدفع
        data: بيانات التحديث
        service: خدمة المدفوعات

    Returns:
        PaymentResponse: الدفع المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على الدفع
    """
    logger.info(
        "api_update_payment",
        extra={
            "payment_id": payment_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    await require_owned_payment(
        payment_id=payment_id,
        owner=owner,
        session=service.session,
    )

    try:
        payment = await service.update_payment(
            payment_id=payment_id,
            update_data=data,
        )
        return payment

    except NotFoundError as e:
        logger.warning(
            "api_payment_not_found_for_update",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_payment_validation_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_payment_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث الدفع",
        )


# ==============================================
# UPDATE PAYMENT STATUS
# ==============================================


@router.patch(
    "/{payment_id}/status",
    response_model=PaymentResponse,
    summary="تحديث حالة الدفع",
    description="تحديث حالة الدفع",
)
async def update_payment_status(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    payment_id: int = Path(..., ge=1, description="معرف الدفع"),
    data: PaymentStatusUpdate,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """
    تحديث حالة الدفع.

    Args:
        payment_id: معرف الدفع
        data: بيانات تحديث الحالة
        service: خدمة المدفوعات

    Returns:
        PaymentResponse: الدفع المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على الدفع أو كانت الحالة غير صالحة
    """
    logger.info(
        "api_update_payment_status",
        extra={
            "payment_id": payment_id,
            "status": data.status,
        },
    )

    await require_owned_payment(
        payment_id=payment_id,
        owner=owner,
        session=service.session,
    )

    try:
        payment = await service.update_payment_status(
            payment_id=payment_id,
            status_data=data,
        )
        return payment

    except NotFoundError as e:
        logger.warning(
            "api_payment_not_found_for_status_update",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_payment_status_validation_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_payment_status_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث حالة الدفع",
        )


# ==============================================
# CONFIRM PAYMENT
# ==============================================


@router.patch(
    "/{payment_id}/confirm",
    response_model=PaymentResponse,
    summary="تأكيد الدفع",
    description="تأكيد الدفع (تعيين الحالة إلى paid)",
)
async def confirm_payment(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    payment_id: int = Path(..., ge=1, description="معرف الدفع"),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """
    تأكيد الدفع.

    Args:
        payment_id: معرف الدفع
        service: خدمة المدفوعات

    Returns:
        PaymentResponse: الدفع المحدث

    Raises:
        HTTPException: إذا فشل التأكيد
    """
    logger.info(
        "api_confirm_payment",
        extra={"payment_id": payment_id},
    )

    await require_owned_payment(
        payment_id=payment_id,
        owner=owner,
        session=service.session,
    )

    try:
        payment = await service.confirm_payment(payment_id=payment_id)
        return payment

    except NotFoundError as e:
        logger.warning(
            "api_payment_not_found_for_confirm",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_confirm_payment_validation_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_confirm_payment_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تأكيد الدفع",
        )


# ==============================================
# FAIL PAYMENT
# ==============================================


@router.patch(
    "/{payment_id}/fail",
    response_model=PaymentResponse,
    summary="فشل الدفع",
    description="تعيين الدفع كفاشل",
)
async def fail_payment(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    payment_id: int = Path(..., ge=1, description="معرف الدفع"),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """
    تعيين الدفع كفاشل.

    Args:
        payment_id: معرف الدفع
        service: خدمة المدفوعات

    Returns:
        PaymentResponse: الدفع المحدث

    Raises:
        HTTPException: إذا فشلت العملية
    """
    logger.info(
        "api_fail_payment",
        extra={"payment_id": payment_id},
    )

    await require_owned_payment(
        payment_id=payment_id,
        owner=owner,
        session=service.session,
    )

    try:
        payment = await service.fail_payment(payment_id=payment_id)
        return payment

    except NotFoundError as e:
        logger.warning(
            "api_payment_not_found_for_fail",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_fail_payment_validation_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_fail_payment_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تعيين الدفع كفاشل",
        )


# ==============================================
# CANCEL PAYMENT
# ==============================================


@router.patch(
    "/{payment_id}/cancel",
    response_model=PaymentResponse,
    summary="إلغاء الدفع",
    description="إلغاء الدفع",
)
async def cancel_payment(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    payment_id: int = Path(..., ge=1, description="معرف الدفع"),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """
    إلغاء الدفع.

    Args:
        payment_id: معرف الدفع
        service: خدمة المدفوعات

    Returns:
        PaymentResponse: الدفع المحدث

    Raises:
        HTTPException: إذا فشلت العملية
    """
    logger.info(
        "api_cancel_payment",
        extra={"payment_id": payment_id},
    )

    await require_owned_payment(
        payment_id=payment_id,
        owner=owner,
        session=service.session,
    )

    try:
        payment = await service.cancel_payment(payment_id=payment_id)
        return payment

    except NotFoundError as e:
        logger.warning(
            "api_payment_not_found_for_cancel",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_cancel_payment_validation_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_cancel_payment_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إلغاء الدفع",
        )


# ==============================================
# REFUND PAYMENT
# ==============================================


@router.patch(
    "/{payment_id}/refund",
    response_model=PaymentResponse,
    summary="استرداد الدفع",
    description="استرداد الدفع (تعيين الحالة إلى refunded)",
)
async def refund_payment(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    payment_id: int = Path(..., ge=1, description="معرف الدفع"),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """
    استرداد الدفع.

    Args:
        payment_id: معرف الدفع
        service: خدمة المدفوعات

    Returns:
        PaymentResponse: الدفع المحدث

    Raises:
        HTTPException: إذا فشلت العملية
    """
    logger.info(
        "api_refund_payment",
        extra={"payment_id": payment_id},
    )

    await require_owned_payment(
        payment_id=payment_id,
        owner=owner,
        session=service.session,
    )

    try:
        payment = await service.refund_payment(payment_id=payment_id)
        return payment

    except NotFoundError as e:
        logger.warning(
            "api_payment_not_found_for_refund",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_refund_payment_validation_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_refund_payment_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء استرداد الدفع",
        )


# ==============================================
# DELETE PAYMENT
# ==============================================


@router.delete(
    "/{payment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف دفع",
    description="حذف دفع موجود",
)
async def delete_payment(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    payment_id: int = Path(..., ge=1, description="معرف الدفع"),
    service: PaymentService = Depends(get_payment_service),
) -> None:
    """
    حذف دفع.

    Args:
        payment_id: معرف الدفع
        service: خدمة المدفوعات

    Raises:
        HTTPException: إذا لم يتم العثور على الدفع أو كان مدفوعاً/معلقاً
    """
    logger.info(
        "api_delete_payment",
        extra={"payment_id": payment_id},
    )

    await require_owned_payment(
        payment_id=payment_id,
        owner=owner,
        session=service.session,
    )

    try:
        await service.delete_payment(payment_id=payment_id)

    except NotFoundError as e:
        logger.warning(
            "api_payment_not_found_for_delete",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_delete_payment_validation_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_payment_error",
            extra={
                "payment_id": payment_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف الدفع",
        )

    logger.info(
        "api_payment_deleted_successfully",
        extra={"payment_id": payment_id},
    )


# ==============================================
# GET PAYMENT SUMMARY
# ==============================================


@router.get(
    "/stats/summary",
    response_model=PaymentSummary,
    summary="ملخص المدفوعات",
    description="الحصول على ملخص المدفوعات",
)
async def get_payment_summary(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    owner_id: Optional[int] = Query(
        None,
        description="معرف المالك (اختياري)",
        ge=1,
    ),
    restaurant_id: Optional[int] = Query(
        None,
        description="معرف المطعم (اختياري)",
        ge=1,
    ),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentSummary:
    """
    الحصول على ملخص المدفوعات.

    Args:
        owner_id: معرف المالك للتصفية
        restaurant_id: معرف المطعم للتصفية
        service: خدمة المدفوعات

    Returns:
        PaymentSummary: ملخص المدفوعات
    """
    logger.info(
        "api_get_payment_summary",
        extra={
            "owner_id": owner_id,
            "restaurant_id": restaurant_id,
        },
    )

    if owner_id is not None and owner_id != owner.owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another owner's payment summary",
        )
    if restaurant_id is not None:
        await require_owned_restaurant(
            restaurant_id=restaurant_id,
            owner=owner,
            session=service.session,
        )

    try:
        summary = await service.get_payment_summary(
            restaurant_id=restaurant_id,
            owner_id=owner.owner_id,
        )
        return summary

    except Exception as e:
        logger.exception(
            "api_get_payment_summary_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب ملخص المدفوعات",
        )


# ==============================================
# GET SUBSCRIPTION PAYMENTS
# ==============================================


@router.get(
    "/subscription/{subscription_id}",
    response_model=PaymentListResponse,
    summary="مدفوعات الاشتراك",
    description="الحصول على مدفوعات اشتراك معين",
)
async def get_subscription_payments(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    subscription_id: int = Path(..., ge=1, description="معرف الاشتراك"),
    skip: int = Query(
        0,
        ge=0,
        description="عدد السجلات للتخطي",
    ),
    limit: int = Query(
        100,
        ge=1,
        le=200,
        description="الحد الأقصى للسجلات",
    ),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentListResponse:
    """
    الحصول على مدفوعات اشتراك معين.

    Args:
        subscription_id: معرف الاشتراك
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة المدفوعات

    Returns:
        PaymentListResponse: قائمة مدفوعات الاشتراك مع الإحصائيات
    """
    logger.info(
        "api_get_subscription_payments",
        extra={
            "subscription_id": subscription_id,
            "skip": skip,
            "limit": limit,
        },
    )

    await require_owned_subscription(
        subscription_id=subscription_id,
        owner=owner,
        session=service.session,
    )

    try:
        payments = await service.get_by_subscription(
            subscription_id=subscription_id,
            skip=skip,
            limit=limit,
        )

        total = len(payments)

        return PaymentListResponse(
            items=payments,
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_get_subscription_payments_error",
            extra={
                "subscription_id": subscription_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب مدفوعات الاشتراك",
        )
