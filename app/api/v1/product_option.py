# ==============================================
# 🎯 PRODUCT OPTIONS API
# نقاط نهاية API لخيارات المنتج
# تدير عمليات إنشاء واستعراض وتحديث وحذف خيارات المنتج
# ==============================================

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

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

from app.core.database import get_db
from app.core.logger import logger
from app.schemas.product_option import (
    ProductOptionAvailabilityUpdate,
    ProductOptionBulkCreate,
    ProductOptionCreate,
    ProductOptionResponse,
    ProductOptionSummary,
    ProductOptionUpdate,
    ProductOptionListResponse,
)
from app.services.business.option_groups_service import OptionGroupsService
from app.services.business.product_option_service import ProductOptionService

# ==============================================
# 🧩 TYPES
# ==============================================

ProductOptionList = List[ProductOptionResponse]


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/product-options",
    tags=["Product Options"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================

async def get_product_option_service(
    session: AsyncSession = Depends(get_db),
) -> ProductOptionService:
    """
    الحصول على خدمة خيارات المنتج.
    
    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        ProductOptionService: مثيل من ProductOptionService
    """
    return ProductOptionService(session)


async def get_option_groups_service(
    session: AsyncSession = Depends(get_db),
) -> OptionGroupsService:
    """
    الحصول على خدمة مجموعات الخيارات.
    
    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        OptionGroupsService: مثيل من OptionGroupsService
    """
    return OptionGroupsService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# LIST PRODUCT OPTIONS
# ==============================================

@router.get(
    "/",
    response_model=ProductOptionListResponse,
    summary="قائمة خيارات المنتج",
    description="الحصول على قائمة خيارات المنتج مع إمكانية التصفية",
)
async def list_product_options(
    *,
    group_id: Optional[int] = Query(
        None,
        description="معرف مجموعة الخيارات",
        ge=1,
    ),
    search: Optional[str] = Query(
        None,
        min_length=1,
        max_length=255,
        description="نص البحث",
    ),
    only_available: bool = Query(
        True,
        description="جلب الخيارات المتاحة فقط",
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
    service: ProductOptionService = Depends(get_product_option_service),
) -> ProductOptionListResponse:
    """
    الحصول على قائمة خيارات المنتج.
    
    Args:
        group_id: معرف مجموعة الخيارات للتصفية
        search: نص البحث
        only_available: جلب الخيارات المتاحة فقط
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة خيارات المنتج
        
    Returns:
        ProductOptionListResponse: قائمة خيارات المنتج مع الإحصائيات
    """
    logger.info(
        "api_list_product_options",
        extra={
            "group_id": group_id,
            "search": search,
            "only_available": only_available,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        if search is not None:
            result = await service.search(
                query=search,
                group_id=group_id,
                skip=skip,
                limit=limit,
                only_available=only_available,
            )
        elif group_id is not None:
            result = await service.get_by_group(
                group_id=group_id,
                skip=skip,
                limit=limit,
                only_available=only_available,
            )
        else:
            # جلب جميع الخيارات
            filters = {}
            if only_available:
                filters["is_available"] = True

            options = await service.repo.get_all(
                skip=skip,
                limit=limit,
                filters=filters,
                order_by="sort_order",
            )
            total = await service.repo.count(filters=filters)
            
            result = ProductOptionListResponse(
                items=[ProductOptionResponse.model_validate(o) for o in options],
                total=total,
                skip=skip,
                limit=limit,
            )

        return result

    except Exception as e:
        logger.exception(
            "api_list_product_options_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة خيارات المنتج",
        )


# ==============================================
# GET GROUP OPTIONS
# ==============================================

@router.get(
    "/group/{group_id}",
    response_model=ProductOptionListResponse,
    summary="خيارات مجموعة",
    description="الحصول على خيارات مجموعة معينة",
)
async def get_group_options(
    *,
    group_id: int = Path(..., ge=1, description="معرف مجموعة الخيارات"),
    only_available: bool = Query(
        True,
        description="جلب الخيارات المتاحة فقط",
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
    service: ProductOptionService = Depends(get_product_option_service),
) -> ProductOptionListResponse:
    """
    الحصول على خيارات مجموعة معينة.
    
    Args:
        group_id: معرف مجموعة الخيارات
        only_available: جلب الخيارات المتاحة فقط
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة خيارات المنتج
        
    Returns:
        ProductOptionListResponse: قائمة خيارات المنتج مع الإحصائيات
    """
    logger.info(
        "api_get_group_options",
        extra={
            "group_id": group_id,
            "only_available": only_available,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        result = await service.get_by_group(
            group_id=group_id,
            skip=skip,
            limit=limit,
            only_available=only_available,
        )
        return result

    except Exception as e:
        logger.exception(
            "api_get_group_options_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب خيارات المجموعة",
        )


# ==============================================
# GET PRODUCT OPTION BY ID
# ==============================================

@router.get(
    "/{option_id}",
    response_model=ProductOptionResponse,
    summary="خيار منتج بالمعرف",
    description="الحصول على خيار منتج محدد",
)
async def get_product_option(
    *,
    option_id: int = Path(..., ge=1, description="معرف الخيار"),
    service: ProductOptionService = Depends(get_product_option_service),
) -> ProductOptionResponse:
    """
    الحصول على خيار منتج محدد.
    
    Args:
        option_id: معرف الخيار
        service: خدمة خيارات المنتج
        
    Returns:
        ProductOptionResponse: خيار المنتج
        
    Raises:
        HTTPException: إذا لم يتم العثور على الخيار
    """
    logger.info(
        "api_get_product_option",
        extra={"option_id": option_id},
    )

    try:
        option = await service.get_by_id(
            option_id=option_id,
        )
        return option

    except NotFoundError as e:
        logger.warning(
            "api_product_option_not_found",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_product_option_error",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب خيار المنتج",
        )


# ==============================================
# CREATE PRODUCT OPTION
# ==============================================

@router.post(
    "/",
    response_model=ProductOptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء خيار منتج",
    description="إنشاء خيار منتج جديد",
)
async def create_product_option(
    *,
    data: ProductOptionCreate,
    group_id: int = Query(
        ...,
        description="معرف مجموعة الخيارات",
        ge=1,
    ),
    service: ProductOptionService = Depends(get_product_option_service),
) -> ProductOptionResponse:
    """
    إنشاء خيار منتج جديد.
    
    Args:
        data: بيانات الخيار
        group_id: معرف مجموعة الخيارات
        service: خدمة خيارات المنتج
        
    Returns:
        ProductOptionResponse: خيار المنتج المنشأ
        
    Raises:
        HTTPException: إذا حدث خطأ أثناء الإنشاء
    """
    logger.info(
        "api_create_product_option",
        extra={
            "group_id": group_id,
            "product_option_name": data.name,
            "extra_price": data.extra_price,
        },
    )

    try:
        # إضافة group_id إلى البيانات
        data.group_id = group_id
        option = await service.create_option(
            option_data=data,
        )
        return option

    except NotFoundError as e:
        logger.warning(
            "api_create_product_option_group_not_found",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_create_product_option_conflict",
            extra={
                "group_id": group_id,
                "product_option_name": data.name,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_product_option_validation_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_product_option_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء خيار المنتج",
        )


# ==============================================
# CREATE PRODUCT OPTIONS BULK
# ==============================================

@router.post(
    "/bulk",
    response_model=ProductOptionListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء عدة خيارات دفعة واحدة",
    description="إنشاء عدة خيارات منتج دفعة واحدة",
)
async def create_product_options_bulk(
    *,
    data: ProductOptionBulkCreate,
    service: ProductOptionService = Depends(get_product_option_service),
) -> ProductOptionListResponse:
    """
    إنشاء عدة خيارات منتج دفعة واحدة.
    
    Args:
        data: بيانات الخيارات
        service: خدمة خيارات المنتج
        
    Returns:
        ProductOptionListResponse: قائمة خيارات المنتج المنشأة مع الإحصائيات
    """
    logger.info(
        "api_create_product_options_bulk",
        extra={
            "group_id": data.group_id,
            "count": len(data.options),
        },
    )

    created_options = []

    try:
        for option_data in data.options:
            option = await service.create_option(
                option_data=option_data,
            )
            created_options.append(option)

        return ProductOptionListResponse(
            items=[ProductOptionResponse.model_validate(o) for o in created_options],
            total=len(created_options),
            skip=0,
            limit=len(created_options),
        )

    except NotFoundError as e:
        logger.warning(
            "api_create_product_options_bulk_group_not_found",
            extra={
                "group_id": data.group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_create_product_options_bulk_conflict",
            extra={
                "group_id": data.group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_product_options_bulk_validation_error",
            extra={
                "group_id": data.group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_product_options_bulk_error",
            extra={
                "group_id": data.group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء خيارات المنتج دفعة واحدة",
        )


# ==============================================
# UPDATE PRODUCT OPTION
# ==============================================

@router.patch(
    "/{option_id}",
    response_model=ProductOptionResponse,
    summary="تحديث خيار منتج",
    description="تحديث خيار منتج موجود",
)
async def update_product_option(
    *,
    option_id: int = Path(..., ge=1, description="معرف الخيار"),
    data: ProductOptionUpdate,
    service: ProductOptionService = Depends(get_product_option_service),
) -> ProductOptionResponse:
    """
    تحديث خيار منتج موجود.
    
    Args:
        option_id: معرف الخيار
        data: بيانات التحديث
        service: خدمة خيارات المنتج
        
    Returns:
        ProductOptionResponse: خيار المنتج المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على الخيار أو حدث تعارض
    """
    logger.info(
        "api_update_product_option",
        extra={
            "option_id": option_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        option = await service.update_option(
            option_id=option_id,
            update_data=data,
        )
        return option

    except NotFoundError as e:
        logger.warning(
            "api_product_option_not_found_for_update",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_update_product_option_conflict",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_product_option_validation_error",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_product_option_error",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث خيار المنتج",
        )


# ==============================================
# UPDATE PRODUCT OPTION AVAILABILITY
# ==============================================

@router.patch(
    "/{option_id}/availability",
    response_model=ProductOptionResponse,
    summary="تحديث حالة توفر الخيار",
    description="تفعيل أو إلغاء تفعيل خيار المنتج",
)
async def update_product_option_availability(
    *,
    option_id: int = Path(..., ge=1, description="معرف الخيار"),
    data: ProductOptionAvailabilityUpdate,
    service: ProductOptionService = Depends(get_product_option_service),
) -> ProductOptionResponse:
    """
    تحديث حالة توفر خيار المنتج.
    
    Args:
        option_id: معرف الخيار
        data: بيانات تحديث التوفر
        service: خدمة خيارات المنتج
        
    Returns:
        ProductOptionResponse: خيار المنتج المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على الخيار
    """
    logger.info(
        "api_update_product_option_availability",
        extra={
            "option_id": option_id,
            "is_available": data.is_available,
        },
    )

    try:
        option = await service.update_availability(
            option_id=option_id,
            availability_data=data,
        )
        return option

    except NotFoundError as e:
        logger.warning(
            "api_product_option_not_found_for_availability",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_product_option_availability_error",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث حالة توفر الخيار",
        )


# ==============================================
# UPDATE PRODUCT OPTION PRICE
# ==============================================

@router.patch(
    "/{option_id}/price",
    response_model=ProductOptionResponse,
    summary="تحديث سعر الخيار",
    description="تحديث السعر الإضافي لخيار المنتج",
)
async def update_product_option_price(
    *,
    option_id: int = Path(..., ge=1, description="معرف الخيار"),
    extra_price: float = Query(
        ...,
        ge=0,
        description="السعر الإضافي الجديد",
    ),
    service: ProductOptionService = Depends(get_product_option_service),
) -> ProductOptionResponse:
    """
    تحديث السعر الإضافي لخيار المنتج.
    
    Args:
        option_id: معرف الخيار
        extra_price: السعر الإضافي الجديد
        service: خدمة خيارات المنتج
        
    Returns:
        ProductOptionResponse: خيار المنتج المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على الخيار
    """
    logger.info(
        "api_update_product_option_price",
        extra={
            "option_id": option_id,
            "extra_price": extra_price,
        },
    )

    try:
        option = await service.update_price(
            option_id=option_id,
            extra_price=extra_price,
        )
        return option

    except NotFoundError as e:
        logger.warning(
            "api_product_option_not_found_for_price",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_product_option_price_validation_error",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_product_option_price_error",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث سعر الخيار",
        )


# ==============================================
# UPDATE PRODUCT OPTION SORT ORDER
# ==============================================

@router.patch(
    "/{option_id}/sort-order",
    response_model=ProductOptionResponse,
    summary="تحديث ترتيب الخيار",
    description="تحديث ترتيب خيار المنتج",
)
async def update_product_option_sort_order(
    *,
    option_id: int = Path(..., ge=1, description="معرف الخيار"),
    sort_order: int = Query(
        ...,
        ge=0,
        description="الترتيب الجديد",
    ),
    service: ProductOptionService = Depends(get_product_option_service),
) -> ProductOptionResponse:
    """
    تحديث ترتيب خيار المنتج.
    
    Args:
        option_id: معرف الخيار
        sort_order: الترتيب الجديد
        service: خدمة خيارات المنتج
        
    Returns:
        ProductOptionResponse: خيار المنتج المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على الخيار
    """
    logger.info(
        "api_update_product_option_sort_order",
        extra={
            "option_id": option_id,
            "sort_order": sort_order,
        },
    )

    try:
        option = await service.update_sort_order(
            option_id=option_id,
            sort_order=sort_order,
        )
        return option

    except NotFoundError as e:
        logger.warning(
            "api_product_option_not_found_for_sort_order",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_product_option_sort_order_error",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث ترتيب الخيار",
        )


# ==============================================
# REORDER PRODUCT OPTIONS
# ==============================================

@router.post(
    "/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="إعادة ترتيب خيارات المنتج",
    description="إعادة ترتيب خيارات المنتج حسب القائمة المقدمة",
)
async def reorder_product_options(
    *,
    group_id: int = Query(
        ...,
        description="معرف مجموعة الخيارات",
        ge=1,
    ),
    option_order: List[int] = Query(
        ...,
        description="قائمة معرفات الخيارات بالترتيب الجديد",
    ),
    service: ProductOptionService = Depends(get_product_option_service),
) -> None:
    """
    إعادة ترتيب خيارات المنتج.
    
    Args:
        group_id: معرف مجموعة الخيارات
        option_order: قائمة معرفات الخيارات بالترتيب الجديد
        service: خدمة خيارات المنتج
        
    Raises:
        HTTPException: إذا حدث خطأ
    """
    logger.info(
        "api_reorder_product_options",
        extra={
            "group_id": group_id,
            "option_count": len(option_order),
        },
    )

    try:
        await service.reorder_options(
            group_id=group_id,
            option_order=option_order,
        )

    except NotFoundError as e:
        logger.warning(
            "api_reorder_product_options_not_found",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_reorder_product_options_validation_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_reorder_product_options_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إعادة ترتيب خيارات المنتج",
        )


# ==============================================
# DELETE PRODUCT OPTION
# ==============================================

@router.delete(
    "/{option_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف خيار منتج",
    description="حذف خيار منتج موجود",
)
async def delete_product_option(
    *,
    option_id: int = Path(..., ge=1, description="معرف الخيار"),
    service: ProductOptionService = Depends(get_product_option_service),
) -> None:
    """
    حذف خيار منتج موجود.
    
    Args:
        option_id: معرف الخيار
        service: خدمة خيارات المنتج
        
    Raises:
        HTTPException: إذا لم يتم العثور على الخيار
    """
    logger.info(
        "api_delete_product_option",
        extra={"option_id": option_id},
    )

    try:
        await service.delete_option(
            option_id=option_id,
        )

    except NotFoundError as e:
        logger.warning(
            "api_product_option_not_found_for_delete",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_product_option_error",
            extra={
                "option_id": option_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف خيار المنتج",
        )

    logger.info(
        "api_product_option_deleted_successfully",
        extra={"option_id": option_id},
    )


# ==============================================
# DELETE GROUP OPTIONS
# ==============================================

@router.delete(
    "/group/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف جميع خيارات المجموعة",
    description="حذف جميع خيارات مجموعة معينة",
)
async def delete_group_options(
    *,
    group_id: int = Path(..., ge=1, description="معرف مجموعة الخيارات"),
    service: ProductOptionService = Depends(get_product_option_service),
) -> None:
    """
    حذف جميع خيارات مجموعة معينة.
    
    Args:
        group_id: معرف مجموعة الخيارات
        service: خدمة خيارات المنتج
        
    Raises:
        HTTPException: إذا لم يتم العثور على المجموعة
    """
    logger.info(
        "api_delete_group_options",
        extra={"group_id": group_id},
    )

    try:
        await service.delete_by_group(
            group_id=group_id,
        )

    except NotFoundError as e:
        logger.warning(
            "api_group_not_found_for_options_delete",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_group_options_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف خيارات المجموعة",
        )

    logger.info(
        "api_group_options_deleted_successfully",
        extra={"group_id": group_id},
    )


# ==============================================
# GET GROUP OPTIONS SUMMARY
# ==============================================

@router.get(
    "/group/{group_id}/summary",
    response_model=ProductOptionSummary,
    summary="ملخص خيارات المجموعة",
    description="الحصول على ملخص خيارات مجموعة معينة",
)
async def get_group_options_summary(
    *,
    group_id: int = Path(..., ge=1, description="معرف مجموعة الخيارات"),
    service: ProductOptionService = Depends(get_product_option_service),
) -> ProductOptionSummary:
    """
    الحصول على ملخص خيارات مجموعة معينة.
    
    Args:
        group_id: معرف مجموعة الخيارات
        service: خدمة خيارات المنتج
        
    Returns:
        ProductOptionSummary: ملخص خيارات المجموعة
    """
    logger.info(
        "api_get_group_options_summary",
        extra={"group_id": group_id},
    )

    try:
        summary = await service.get_option_summary(
            group_id=group_id,
        )
        return summary

    except Exception as e:
        logger.exception(
            "api_get_group_options_summary_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب ملخص خيارات المجموعة",
        )