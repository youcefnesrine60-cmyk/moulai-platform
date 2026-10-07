# ==============================================
# 📦 ORDER ITEMS API
# نقاط نهاية API لتفاصيل الطلب
# تدير عمليات إنشاء واستعراض وتحديث وحذف تفاصيل الطلب
# ==============================================

from typing import List

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
    require_owned_order,
    require_owned_order_item,
)
# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

from app.core.database import get_db
from app.core.logger import logger
from app.schemas.order_item import (
    OrderItemCreate,
    OrderItemResponse,
    OrderItemSummary,
    OrderItemWithOptionsResponse,
    OrderItemListResponse,
)
from app.services.business.order_items_service import OrderItemsService
from app.services.business.order_item_options_service import OrderItemOptionsService

# ==============================================
# 🧩 TYPES
# ==============================================

OrderItemList = List[OrderItemWithOptionsResponse]
OrderItemResponseList = List[OrderItemResponse]


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/order-items",
    tags=["Order Items"],
)


# ==============================================
# 🔧 DEPENDENCIES
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


async def get_order_item_options_service(
    session: AsyncSession = Depends(get_db),
) -> OrderItemOptionsService:
    """
    الحصول على خدمة خيارات عناصر الطلبات.
    
    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        OrderItemOptionsService: مثيل من OrderItemOptionsService
    """
    return OrderItemOptionsService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# LIST ORDER ITEMS
# ==============================================

@router.get(
    "/",
    response_model=OrderItemListResponse,
    summary="قائمة تفاصيل الطلب",
    description="الحصول على قائمة تفاصيل الطلب لطلب معين",
)
async def list_order_items(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    order_id: int = Query(
        ...,
        description="معرف الطلب",
        ge=1,
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
    service: OrderItemsService = Depends(get_order_items_service),
) -> OrderItemListResponse:
    """
    الحصول على قائمة تفاصيل الطلب لطلب معين.
    
    Args:
        order_id: معرف الطلب
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة عناصر الطلبات
        
    Returns:
        OrderItemListResponse: قائمة تفاصيل الطلب مع الإحصائيات
    """
    logger.info(
        "api_list_order_items",
        extra={
            "order_id": order_id,
            "skip": skip,
            "limit": limit,
        },
    )

    await require_owned_order(
        order_id=order_id,
        owner=owner,
        session=service.session,
    )

    try:
        result = await service.get_by_order(
            order_id=order_id,
            skip=skip,
            limit=limit,
        )
        return result

    except NotFoundError as e:
        logger.warning(
            "api_order_not_found_for_items",
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
            "api_list_order_items_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة تفاصيل الطلب",
        )


# ==============================================
# GET ORDER ITEM BY ID
# ==============================================

@router.get(
    "/{order_item_id}",
    response_model=OrderItemWithOptionsResponse,
    summary="تفاصيل طلب بالمعرف",
    description="الحصول على تفاصيل طلب محددة مع خياراتها",
)
async def get_order_item(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    order_item_id: int = Path(..., ge=1, description="معرف تفاصيل الطلب"),
    service: OrderItemsService = Depends(get_order_items_service),
    options_service: OrderItemOptionsService = Depends(get_order_item_options_service),
) -> OrderItemWithOptionsResponse:
    """
    الحصول على تفاصيل طلب محددة مع خياراتها.
    
    Args:
        order_item_id: معرف تفاصيل الطلب
        service: خدمة عناصر الطلبات
        options_service: خدمة خيارات عناصر الطلبات
        
    Returns:
        OrderItemWithOptionsResponse: تفاصيل الطلب مع الخيارات
        
    Raises:
        HTTPException: إذا لم يتم العثور على تفاصيل الطلب
    """
    logger.info(
        "api_get_order_item",
        extra={"order_item_id": order_item_id},
    )

    await require_owned_order_item(
        order_item_id=order_item_id,
        owner=owner,
        session=service.session,
    )

    try:
        # جلب تفاصيل الطلب مع الخيارات
        item = await service.get_with_options(
            order_item_id=order_item_id,
        )
        return item

    except NotFoundError as e:
        logger.warning(
            "api_order_item_not_found",
            extra={
                "order_item_id": order_item_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_order_item_error",
            extra={
                "order_item_id": order_item_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب تفاصيل الطلب",
        )


# ==============================================
# CREATE ORDER ITEM
# ==============================================

@router.post(
    "/",
    response_model=OrderItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إضافة تفاصيل طلب",
    description="إضافة تفاصيل طلب جديدة إلى طلب موجود",
)
async def create_order_item(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    data: OrderItemCreate,
    service: OrderItemsService = Depends(get_order_items_service),
) -> OrderItemResponse:
    """
    إضافة تفاصيل طلب جديدة إلى طلب موجود.
    
    Args:
        data: بيانات تفاصيل الطلب
        service: خدمة عناصر الطلبات
        
    Returns:
        OrderItemResponse: تفاصيل الطلب المنشأة
        
    Raises:
        HTTPException: إذا حدث خطأ أثناء الإنشاء
    """
    logger.info(
        "api_create_order_item",
        extra={
            "order_id": data.order_id,
            "product_id": data.product_id,
            "quantity": data.quantity,
        },
    )

    await require_owned_order(
        order_id=data.order_id,
        owner=owner,
        session=service.session,
    )

    try:
        item = await service.add_item(
            item_data=data,
        )
        return item

    except NotFoundError as e:
        logger.warning(
            "api_order_not_found_for_item_create",
            extra={
                "order_id": data.order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_create_order_item_conflict",
            extra={
                "order_id": data.order_id,
                "product_id": data.product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_order_item_validation_error",
            extra={
                "order_id": data.order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_order_item_error",
            extra={
                "order_id": data.order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إضافة تفاصيل الطلب",
        )


# ==============================================
# UPDATE ORDER ITEM QUANTITY
# ==============================================

@router.patch(
    "/{order_item_id}/quantity",
    response_model=OrderItemResponse,
    summary="تحديث كمية تفاصيل الطلب",
    description="تحديث كمية تفاصيل طلب موجودة",
)
async def update_order_item_quantity(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    order_item_id: int = Path(..., ge=1, description="معرف تفاصيل الطلب"),
    quantity: int = Query(
        ...,
        ge=1,
        le=100,
        description="الكمية الجديدة",
    ),
    service: OrderItemsService = Depends(get_order_items_service),
) -> OrderItemResponse:
    """
    تحديث كمية تفاصيل طلب موجودة.
    
    Args:
        order_item_id: معرف تفاصيل الطلب
        quantity: الكمية الجديدة
        service: خدمة عناصر الطلبات
        
    Returns:
        OrderItemResponse: تفاصيل الطلب المحدثة
        
    Raises:
        HTTPException: إذا لم يتم العثور على تفاصيل الطلب
    """
    logger.info(
        "api_update_order_item_quantity",
        extra={
            "order_item_id": order_item_id,
            "quantity": quantity,
        },
    )

    await require_owned_order_item(
        order_item_id=order_item_id,
        owner=owner,
        session=service.session,
    )

    try:
        item = await service.update_quantity(
            order_item_id=order_item_id,
            quantity=quantity,
        )
        return item

    except NotFoundError as e:
        logger.warning(
            "api_order_item_not_found_for_update",
            extra={
                "order_item_id": order_item_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_order_item_validation_error",
            extra={
                "order_item_id": order_item_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_order_item_quantity_error",
            extra={
                "order_item_id": order_item_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث كمية تفاصيل الطلب",
        )


# ==============================================
# UPDATE ORDER ITEM UNIT PRICE
# ==============================================

@router.patch(
    "/{order_item_id}/unit-price",
    response_model=OrderItemResponse,
    summary="تحديث سعر الوحدة",
    description="تحديث سعر الوحدة لتفاصيل طلب موجودة",
)
async def update_order_item_unit_price(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    order_item_id: int = Path(..., ge=1, description="معرف تفاصيل الطلب"),
    unit_price: float = Query(
        ...,
        ge=0,
        description="سعر الوحدة الجديد",
    ),
    service: OrderItemsService = Depends(get_order_items_service),
) -> OrderItemResponse:
    """
    تحديث سعر الوحدة لتفاصيل طلب موجودة.
    
    Args:
        order_item_id: معرف تفاصيل الطلب
        unit_price: سعر الوحدة الجديد
        service: خدمة عناصر الطلبات
        
    Returns:
        OrderItemResponse: تفاصيل الطلب المحدثة
        
    Raises:
        HTTPException: إذا لم يتم العثور على تفاصيل الطلب
    """
    logger.info(
        "api_update_order_item_unit_price",
        extra={
            "order_item_id": order_item_id,
            "unit_price": unit_price,
        },
    )

    await require_owned_order_item(
        order_item_id=order_item_id,
        owner=owner,
        session=service.session,
    )

    try:
        item = await service.update_unit_price(
            order_item_id=order_item_id,
            unit_price=unit_price,
        )
        return item

    except NotFoundError as e:
        logger.warning(
            "api_order_item_not_found_for_unit_price",
            extra={
                "order_item_id": order_item_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_order_item_unit_price_validation_error",
            extra={
                "order_item_id": order_item_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_order_item_unit_price_error",
            extra={
                "order_item_id": order_item_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث سعر الوحدة",
        )


# ==============================================
# DELETE ORDER ITEM
# ==============================================

@router.delete(
    "/{order_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف تفاصيل طلب",
    description="حذف تفاصيل طلب موجودة",
)
async def delete_order_item(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    order_item_id: int = Path(..., ge=1, description="معرف تفاصيل الطلب"),
    service: OrderItemsService = Depends(get_order_items_service),
) -> None:
    """
    حذف تفاصيل طلب موجودة.
    
    Args:
        order_item_id: معرف تفاصيل الطلب
        service: خدمة عناصر الطلبات
        
    Raises:
        HTTPException: إذا لم يتم العثور على تفاصيل الطلب
    """
    logger.info(
        "api_delete_order_item",
        extra={"order_item_id": order_item_id},
    )

    await require_owned_order_item(
        order_item_id=order_item_id,
        owner=owner,
        session=service.session,
    )

    try:
        await service.remove_item(
            order_item_id=order_item_id,
        )

    except NotFoundError as e:
        logger.warning(
            "api_order_item_not_found_for_delete",
            extra={
                "order_item_id": order_item_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_order_item_error",
            extra={
                "order_item_id": order_item_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف تفاصيل الطلب",
        )

    logger.info(
        "api_order_item_deleted_successfully",
        extra={"order_item_id": order_item_id},
    )


# ==============================================
# DELETE ALL ORDER ITEMS
# ==============================================

@router.delete(
    "/order/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف جميع تفاصيل الطلب",
    description="حذف جميع تفاصيل طلب معين",
)
async def delete_all_order_items(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    order_id: int = Path(..., ge=1, description="معرف الطلب"),
    service: OrderItemsService = Depends(get_order_items_service),
) -> None:
    """
    حذف جميع تفاصيل طلب معين.
    
    Args:
        order_id: معرف الطلب
        service: خدمة عناصر الطلبات
        
    Raises:
        HTTPException: إذا لم يتم العثور على الطلب
    """
    logger.info(
        "api_delete_all_order_items",
        extra={"order_id": order_id},
    )

    await require_owned_order(
        order_id=order_id,
        owner=owner,
        session=service.session,
    )

    try:
        await service.remove_all_items(
            order_id=order_id,
        )

    except NotFoundError as e:
        logger.warning(
            "api_order_not_found_for_items_delete",
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
            "api_delete_all_order_items_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف جميع تفاصيل الطلب",
        )

    logger.info(
        "api_all_order_items_deleted_successfully",
        extra={"order_id": order_id},
    )


# ==============================================
# GET ORDER ITEMS SUMMARY
# ==============================================

@router.get(
    "/stats/summary",
    response_model=OrderItemSummary,
    summary="ملخص تفاصيل الطلب",
    description="الحصول على ملخص تفاصيل الطلب لطلب معين",
)
async def get_order_items_summary(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    order_id: int = Query(
        ...,
        description="معرف الطلب",
        ge=1,
    ),
    service: OrderItemsService = Depends(get_order_items_service),
) -> OrderItemSummary:
    """
    الحصول على ملخص تفاصيل الطلب.
    
    Args:
        order_id: معرف الطلب
        service: خدمة عناصر الطلبات
        
    Returns:
        OrderItemSummary: ملخص تفاصيل الطلب
        
    Raises:
        HTTPException: إذا حدث خطأ
    """
    logger.info(
        "api_get_order_items_summary",
        extra={"order_id": order_id},
    )

    await require_owned_order(
        order_id=order_id,
        owner=owner,
        session=service.session,
    )

    try:
        summary = await service.get_item_summary(
            order_id=order_id,
        )
        return summary

    except NotFoundError as e:
        logger.warning(
            "api_order_not_found_for_summary",
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
            "api_get_order_items_summary_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب ملخص تفاصيل الطلب",
        )


# ==============================================
# CREATE ORDER ITEMS BATCH
# ==============================================

@router.post(
    "/batch",
    response_model=OrderItemListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إضافة عدة تفاصيل طلب",
    description="إضافة عدة تفاصيل طلب دفعة واحدة",
)
async def create_order_items_batch(
    *,
    owner: OwnerPrincipal = Depends(get_current_owner),
    items: List[OrderItemCreate],
    service: OrderItemsService = Depends(get_order_items_service),
) -> OrderItemListResponse:
    """
    إضافة عدة تفاصيل طلب دفعة واحدة.
    
    Args:
        items: قائمة بيانات تفاصيل الطلب
        service: خدمة عناصر الطلبات
        
    Returns:
        OrderItemListResponse: قائمة تفاصيل الطلب المنشأة مع الإحصائيات
        
    Raises:
        HTTPException: إذا كانت القائمة فارغة أو حدث خطأ
    """
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No items provided",
        )

    # التحقق من أن جميع العناصر لنفس الطلب
    order_id = items[0].order_id

    for item in items:
        if item.order_id != order_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All items must belong to the same order",
            )

    logger.info(
        "api_create_order_items_batch",
        extra={
            "order_id": order_id,
            "count": len(items),
        },
    )

    await require_owned_order(
        order_id=order_id,
        owner=owner,
        session=service.session,
    )

    created_items = []

    try:
        for item_data in items:
            item = await service.add_item(
                item_data=item_data,
            )
            created_items.append(item)

        return OrderItemListResponse(
            items=[OrderItemResponse.model_validate(item) for item in created_items],
            total=len(created_items),
            skip=0,
            limit=len(created_items),
        )

    except NotFoundError as e:
        logger.warning(
            "api_order_not_found_for_batch",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_create_order_items_batch_conflict",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_order_items_batch_validation_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_order_items_batch_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إضافة تفاصيل الطلب دفعة واحدة",
        )