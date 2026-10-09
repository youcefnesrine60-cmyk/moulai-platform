# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📦 ORDERS API
# نقاط نهاية API للطلبات
# تدير عمليات إنشاء واستعراض وتحديث وحذف الطلبات
# ==============================================

"""MoulAI operational module for orders.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    List,
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
    get_current_owner,
    require_owned_order,
    require_owned_restaurant,
    OwnerPrincipal,
)

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

from app.core.database import get_db
from app.core.logger import logger
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
    OrderSummary,
    OrderUpdate,
    OrderWithItemsResponse,
    OrderListResponse,
)
from app.services.business.order_service import OrderService
from app.services.business.order_items_service import OrderItemsService

# ==============================================
# 🧩 TYPES
# ==============================================

OrderList = List[OrderResponse]


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================


async def get_order_service(
    session: AsyncSession = Depends(get_db),
) -> OrderService:
    """
    الحصول على خدمة الطلبات.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        OrderService: مثيل من OrderService
    """
    return OrderService(session)


# ==============================================
# GET ORDER ITEMS SERVICE
# ==============================================


async def get_order_items_service(
    session: AsyncSession = Depends(get_db),
) -> OrderItemsService:
    """
    الحصول على خدمة عناصر الطلبات.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        OrderItemsService: مثيل من OrderItemsService
    """
    return OrderItemsService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# LIST ORDERS
# ==============================================


@router.get(
    "/",
    response_model=OrderListResponse,
    summary="قائمة الطلبات",
    description="الحصول على قائمة الطلبات مع إمكانية التصفية",
)
async def list_orders(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    restaurant_id: Optional[int] = Query(
        None,
        description="معرف المطعم",
        ge=1,
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="حالة الطلب",
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
    service: OrderService = Depends(get_order_service),
) -> OrderListResponse:
    """
    الحصول على قائمة الطلبات.

    Args:
        restaurant_id: معرف المطعم للتصفية
        status_filter: حالة الطلب للتصفية
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة الطلبات

    Returns:
        OrderListResponse: قائمة الطلبات مع الإحصائيات
    """
    logger.info(
        "api_list_orders",
        extra={
            "restaurant_id": restaurant_id,
            "status": status_filter,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        if restaurant_id is None:
            raise ValidationError(
                message="معرف المطعم مطلوب",
            )
        await require_owned_restaurant(
            restaurant_id=restaurant_id,
            owner=owner,
            session=service.session,
        )

        if status_filter is not None:
            result = await service.get_by_status(
                restaurant_id=restaurant_id,
                status=status_filter,
                skip=skip,
                limit=limit,
            )
        else:
            result = await service.get_by_restaurant(
                restaurant_id=restaurant_id,
                skip=skip,
                limit=limit,
            )

        return result

    except HTTPException:
        raise
    except ValidationError as e:
        logger.warning(
            "api_list_orders_validation_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_list_orders_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة الطلبات",
        )


# ==============================================
# GET ORDER BY ID
# ==============================================


@router.get(
    "/{order_id}",
    response_model=OrderWithItemsResponse,
    summary="طلب بالمعرف",
    description="الحصول على طلب محدد مع جميع تفاصيله",
)
async def get_order(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    order_id: int = Path(..., ge=1, description="معرف الطلب"),
    service: OrderService = Depends(get_order_service),
    items_service: OrderItemsService = Depends(get_order_items_service),
) -> OrderWithItemsResponse:
    """
    الحصول على طلب بالمعرف مع جميع تفاصيله.

    Args:
        order_id: معرف الطلب
        service: خدمة الطلبات
        items_service: خدمة عناصر الطلبات

    Returns:
        OrderWithItemsResponse: الطلب مع جميع تفاصيله

    Raises:
        HTTPException: إذا لم يتم العثور على الطلب
    """
    logger.info(
        "api_get_order",
        extra={"order_id": order_id},
    )

    await require_owned_order(
        order_id=order_id,
        owner=owner,
        session=service.session,
    )

    try:
        # جلب الطلب مع العلاقات
        order = await service.get_with_details(
            order_id=order_id,
        )

        # جلب عناصر الطلب
        items_result = await items_service.get_by_order(
            order_id=order_id,
        )

        # بناء الاستجابة
        return OrderWithItemsResponse(
            id=order.id,
            restaurant_id=order.restaurant_id,
            branch_id=order.branch_id,
            table_id=order.table_id,
            employee_id=order.employee_id,
            order_number=order.order_number,
            order_type=order.order_type,
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            delivery_address=order.delivery_address,
            customer_note=order.customer_note,
            subtotal_amount=order.subtotal_amount,
            discount_amount=order.discount_amount,
            tax_amount=order.tax_amount,
            delivery_amount=order.delivery_amount,
            total_amount=order.total_amount,
            status=order.status,
            payment_status=order.payment_status,
            is_paid=order.is_paid,
            created_at=order.created_at,
            updated_at=order.updated_at,
            items=[item.model_dump() for item in items_result],
        )

    except NotFoundError as e:
        logger.warning(
            "api_order_not_found",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_order_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب الطلب",
        )


# ==============================================
# CREATE ORDER
# ==============================================


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء طلب",
    description="إنشاء طلب جديد",
)
async def create_order(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    data: OrderCreate,
    service: OrderService = Depends(get_order_service),
    items_service: OrderItemsService = Depends(get_order_items_service),
) -> OrderResponse:
    """
    إنشاء طلب جديد.

    Args:
        data: بيانات الطلب
        service: خدمة الطلبات
        items_service: خدمة عناصر الطلبات

    Returns:
        OrderResponse: الطلب المنشأ

    Raises:
        HTTPException: إذا حدث خطأ أثناء الإنشاء
    """
    logger.info(
        "api_create_order",
        extra={
            "restaurant_id": data.restaurant_id,
            "order_type": data.order_type,
            "items_count": len(data.items) if data.items else 0,
        },
    )

    await require_owned_restaurant(
        restaurant_id=data.restaurant_id,
        owner=owner,
        session=service.session,
    )

    try:
        return await service.create_order(order_data=data)

    except NotFoundError as e:
        logger.warning(
            "api_create_order_not_found",
            extra={
                "restaurant_id": data.restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_create_order_conflict",
            extra={
                "restaurant_id": data.restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_order_validation_error",
            extra={
                "restaurant_id": data.restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_order_error",
            extra={
                "restaurant_id": data.restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء الطلب",
        )


# ==============================================
# UPDATE ORDER
# ==============================================


@router.patch(
    "/{order_id}",
    response_model=OrderResponse,
    summary="تحديث طلب",
    description="تحديث طلب موجود",
)
async def update_order(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    order_id: int = Path(..., ge=1, description="معرف الطلب"),
    data: OrderUpdate,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """
    تحديث طلب موجود.

    Args:
        order_id: معرف الطلب
        data: بيانات التحديث
        service: خدمة الطلبات

    Returns:
        OrderResponse: الطلب المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على الطلب أو حدث تعارض
    """
    logger.info(
        "api_update_order",
        extra={
            "order_id": order_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    await require_owned_order(
        order_id=order_id,
        owner=owner,
        session=service.session,
    )

    try:
        order = await service.update_order(
            order_id=order_id,
            update_data=data,
        )
        return order

    except NotFoundError as e:
        logger.warning(
            "api_order_not_found_for_update",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_order_validation_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_order_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث الطلب",
        )


# ==============================================
# UPDATE ORDER STATUS
# ==============================================


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="تحديث حالة الطلب",
    description="تغيير حالة الطلب",
)
async def update_order_status(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    order_id: int = Path(..., ge=1, description="معرف الطلب"),
    data: OrderStatusUpdate,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """
    تغيير حالة الطلب.

    Args:
        order_id: معرف الطلب
        data: بيانات تحديث الحالة
        service: خدمة الطلبات

    Returns:
        OrderResponse: الطلب المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على الطلب
    """
    logger.info(
        "api_update_order_status",
        extra={
            "order_id": order_id,
            "new_status": data.status,
            "employee_id": data.employee_id,
        },
    )

    await require_owned_order(
        order_id=order_id,
        owner=owner,
        session=service.session,
    )

    try:
        order = await service.update_order_status(
            order_id=order_id,
            status_data=data,
        )
        return order

    except NotFoundError as e:
        logger.warning(
            "api_order_not_found_for_status_update",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_order_status_validation_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_order_status_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث حالة الطلب",
        )


# ==============================================
# COMPLETE ORDER
# ==============================================


@router.post(
    "/{order_id}/complete",
    response_model=OrderResponse,
    summary="إكمال الطلب",
    description="إكمال الطلب (تعيين الحالة إلى completed)",
)
async def complete_order_endpoint(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    order_id: int = Path(..., ge=1, description="معرف الطلب"),
    employee_id: Optional[int] = Query(
        None,
        description="معرف الموظف",
        ge=1,
    ),
    note: Optional[str] = Query(
        None,
        max_length=500,
        description="ملاحظة",
    ),
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """
    إكمال الطلب.

    Args:
        order_id: معرف الطلب
        employee_id: معرف الموظف (اختياري)
        note: ملاحظة (اختياري)
        service: خدمة الطلبات

    Returns:
        OrderResponse: الطلب المحدث
    """
    logger.info(
        "api_complete_order",
        extra={
            "order_id": order_id,
            "employee_id": employee_id,
        },
    )

    await require_owned_order(
        order_id=order_id,
        owner=owner,
        session=service.session,
    )

    try:
        order = await service.complete_order(
            order_id=order_id,
            employee_id=employee_id,
            note=note,
        )
        return order

    except NotFoundError as e:
        logger.warning(
            "api_order_not_found_for_complete",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_complete_order_validation_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_complete_order_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إكمال الطلب",
        )


# ==============================================
# CANCEL ORDER
# ==============================================


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    summary="إلغاء الطلب",
    description="إلغاء الطلب",
)
async def cancel_order_endpoint(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    order_id: int = Path(..., ge=1, description="معرف الطلب"),
    employee_id: Optional[int] = Query(
        None,
        description="معرف الموظف",
        ge=1,
    ),
    reason: Optional[str] = Query(
        None,
        max_length=500,
        description="سبب الإلغاء",
    ),
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """
    إلغاء الطلب.

    Args:
        order_id: معرف الطلب
        employee_id: معرف الموظف (اختياري)
        reason: سبب الإلغاء (اختياري)
        service: خدمة الطلبات

    Returns:
        OrderResponse: الطلب المحدث
    """
    logger.info(
        "api_cancel_order",
        extra={
            "order_id": order_id,
            "employee_id": employee_id,
            "reason": reason,
        },
    )

    await require_owned_order(
        order_id=order_id,
        owner=owner,
        session=service.session,
    )

    try:
        order = await service.cancel_order(
            order_id=order_id,
            employee_id=employee_id,
            reason=reason,
        )
        return order

    except NotFoundError as e:
        logger.warning(
            "api_order_not_found_for_cancel",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_cancel_order_validation_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_cancel_order_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إلغاء الطلب",
        )


# ==============================================
# MARK ORDER AS PAID
# ==============================================


@router.post(
    "/{order_id}/paid",
    response_model=OrderResponse,
    summary="تحديد الطلب كمدفوع",
    description="تحديد الطلب كمدفوع",
)
async def mark_order_paid_endpoint(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    order_id: int = Path(..., ge=1, description="معرف الطلب"),
    payment_id: int = Query(
        ...,
        description="معرف الدفعة",
        ge=1,
    ),
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """
    تحديد الطلب كمدفوع.

    Args:
        order_id: معرف الطلب
        payment_id: معرف الدفعة
        service: خدمة الطلبات

    Returns:
        OrderResponse: الطلب المحدث
    """
    logger.info(
        "api_mark_order_paid",
        extra={
            "order_id": order_id,
            "payment_id": payment_id,
        },
    )

    restaurant_id = await require_owned_order(
        order_id=order_id,
        owner=owner,
        session=service.session,
    )

    try:
        order = await service.mark_as_paid(
            order_id=order_id,
            restaurant_id=restaurant_id,
            payment_id=payment_id,
        )
        return order

    except NotFoundError as e:
        logger.warning(
            "api_order_not_found_for_paid",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_mark_order_paid_validation_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_mark_order_paid_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث حالة الدفع",
        )


# ==============================================
# DELETE ORDER
# ==============================================


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف طلب",
    description="حذف طلب موجود",
)
async def delete_order(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    order_id: int = Path(..., ge=1, description="معرف الطلب"),
    permanent: bool = Query(
        False,
        description="حذف نهائي (بدلاً من الحذف المنطقي)",
    ),
    service: OrderService = Depends(get_order_service),
) -> None:
    """
    حذف طلب.

    Args:
        order_id: معرف الطلب
        permanent: حذف نهائي
        service: خدمة الطلبات

    Raises:
        HTTPException: إذا لم يتم العثور على الطلب
    """
    logger.info(
        "api_delete_order",
        extra={
            "order_id": order_id,
            "permanent": permanent,
        },
    )

    await require_owned_order(
        order_id=order_id,
        owner=owner,
        session=service.session,
    )

    try:
        await service.delete_order(
            order_id=order_id,
            permanent=permanent,
        )

    except NotFoundError as e:
        logger.warning(
            "api_order_not_found_for_delete",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_delete_order_validation_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_order_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف الطلب",
        )

    logger.info(
        "api_order_deleted_successfully",
        extra={
            "order_id": order_id,
            "permanent": permanent,
        },
    )


# ==============================================
# GET ORDER SUMMARY
# ==============================================


@router.get(
    "/stats/summary",
    response_model=OrderSummary,
    summary="ملخص الطلبات",
    description="الحصول على ملخص الطلبات لمطعم معين",
)
async def get_order_summary(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    restaurant_id: int = Query(
        ...,
        description="معرف المطعم",
        ge=1,
    ),
    service: OrderService = Depends(get_order_service),
) -> OrderSummary:
    """
    الحصول على ملخص الطلبات.

    Args:
        restaurant_id: معرف المطعم
        service: خدمة الطلبات

    Returns:
        OrderSummary: ملخص الطلبات

    Raises:
        HTTPException: إذا حدث خطأ
    """
    logger.info(
        "api_get_order_summary",
        extra={"restaurant_id": restaurant_id},
    )

    await require_owned_restaurant(
        restaurant_id=restaurant_id,
        owner=owner,
        session=service.session,
    )

    try:
        summary = await service.get_order_summary(
            restaurant_id=restaurant_id,
        )
        return summary

    except Exception as e:
        logger.exception(
            "api_get_order_summary_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب ملخص الطلبات",
        )
