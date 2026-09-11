# ==============================================
# 🍔 PRODUCTS API
# نقاط نهاية API للمنتجات
# تدير عمليات إنشاء واستعراض وتحديث وحذف المنتجات
# ==============================================

from typing import Optional

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
from app.schemas.product import (
    ProductAvailabilityUpdate,
    ProductCreate,
    ProductResponse,
    ProductSummary,
    ProductUpdate,
    ProductListResponse,
)
from app.services.business.product_service import ProductService

# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================

async def get_product_service(
    session: AsyncSession = Depends(get_db),
) -> ProductService:
    """
    الحصول على خدمة المنتجات.
    
    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        ProductService: مثيل من ProductService
    """
    return ProductService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# LIST PRODUCTS
# ==============================================

@router.get(
    "/",
    response_model=ProductListResponse,
    summary="قائمة المنتجات",
    description="الحصول على قائمة المنتجات مع إمكانية التصفية",
)
async def list_products(
    *,
    restaurant_id: Optional[int] = Query(
        None,
        description="معرف المطعم",
        ge=1,
    ),
    category_id: Optional[int] = Query(
        None,
        description="معرف التصنيف",
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
        description="جلب المنتجات المتاحة فقط",
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
    service: ProductService = Depends(get_product_service),
) -> ProductListResponse:
    """
    الحصول على قائمة المنتجات.
    
    Args:
        restaurant_id: معرف المطعم للتصفية
        category_id: معرف التصنيف للتصفية
        search: نص البحث
        only_available: جلب المنتجات المتاحة فقط
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة المنتجات
        
    Returns:
        ProductListResponse: قائمة المنتجات مع الإحصائيات
    """
    logger.info(
        "api_list_products",
        extra={
            "restaurant_id": restaurant_id,
            "category_id": category_id,
            "search": search,
            "only_available": only_available,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        # تحديد طريقة الجلب بناءً على معايير التصفية
        if search is not None:
            result = await service.search(
                query=search,
                restaurant_id=restaurant_id,
                skip=skip,
                limit=limit,
            )
        elif category_id is not None:
            result = await service.get_by_category(
                category_id=category_id,
                skip=skip,
                limit=limit,
                only_available=only_available,
            )
        elif restaurant_id is not None:
            result = await service.get_by_restaurant(
                restaurant_id=restaurant_id,
                skip=skip,
                limit=limit,
                only_available=only_available,
            )
        else:
            # جلب جميع المنتجات (مع مراعاة التحديدات)
            filters = {}
            if only_available:
                filters["is_available"] = True

            products = await service.repo.get_all(
                skip=skip,
                limit=limit,
                filters=filters,
                order_by="name",
            )
            total = await service.repo.count(filters=filters)
            
            result = ProductListResponse(
                items=[ProductResponse.model_validate(p) for p in products],
                total=total,
                skip=skip,
                limit=limit,
            )

        return result

    except Exception as e:
        logger.exception(
            "api_list_products_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة المنتجات",
        )


# ==============================================
# GET PRODUCT BY ID
# ==============================================

@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="منتج بالمعرف",
    description="الحصول على منتج محدد",
)
async def get_product(
    *,
    product_id: int = Path(..., ge=1, description="معرف المنتج"),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    الحصول على منتج بالمعرف.
    
    Args:
        product_id: معرف المنتج
        service: خدمة المنتجات
        
    Returns:
        ProductResponse: المنتج المطلوب
        
    Raises:
        HTTPException: إذا لم يتم العثور على المنتج
    """
    logger.info(
        "api_get_product",
        extra={"product_id": product_id},
    )

    try:
        product = await service.get_by_id(product_id=product_id)
        return product

    except NotFoundError as e:
        logger.warning(
            "api_product_not_found",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_product_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب المنتج",
        )


# ==============================================
# CREATE PRODUCT
# ==============================================

@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء منتج",
    description="إنشاء منتج جديد",
)
async def create_product(
    *,
    data: ProductCreate,
    restaurant_id: int = Query(
        ...,
        description="معرف المطعم",
        ge=1,
    ),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    إنشاء منتج جديد.
    
    Args:
        data: بيانات المنتج
        restaurant_id: معرف المطعم
        service: خدمة المنتجات
        
    Returns:
        ProductResponse: المنتج المنشأ
        
    Raises:
        HTTPException: إذا حدث خطأ أثناء الإنشاء
    """
    logger.info(
        "api_create_product",
        extra={
            "restaurant_id": restaurant_id,
            "product_name": data.name,
            "price": data.price,
        },
    )

    try:
        # إضافة restaurant_id إلى البيانات
        data.restaurant_id = restaurant_id
        product = await service.create_product(
            product_data=data,
        )
        return product

    except NotFoundError as e:
        logger.warning(
            "api_create_product_not_found",
            extra={
                "restaurant_id": restaurant_id,
                "category_id": data.category_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_create_product_conflict",
            extra={
                "restaurant_id": restaurant_id,
                "product_name": data.name,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_product_validation_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_product_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء المنتج",
        )


# ==============================================
# UPDATE PRODUCT
# ==============================================

@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="تحديث منتج",
    description="تحديث منتج موجود",
)
async def update_product(
    *,
    product_id: int = Path(..., ge=1, description="معرف المنتج"),
    data: ProductUpdate,
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    تحديث منتج موجود.
    
    Args:
        product_id: معرف المنتج
        data: بيانات التحديث
        service: خدمة المنتجات
        
    Returns:
        ProductResponse: المنتج المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على المنتج أو حدث تعارض
    """
    logger.info(
        "api_update_product",
        extra={
            "product_id": product_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        product = await service.update_product(
            product_id=product_id,
            update_data=data,
        )
        return product

    except NotFoundError as e:
        logger.warning(
            "api_product_not_found_for_update",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_update_product_conflict",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_product_validation_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_product_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث المنتج",
        )


# ==============================================
# UPDATE PRODUCT AVAILABILITY
# ==============================================

@router.patch(
    "/{product_id}/availability",
    response_model=ProductResponse,
    summary="تحديث حالة توفر المنتج",
    description="تفعيل أو إلغاء تفعيل منتج",
)
async def update_product_availability(
    *,
    product_id: int = Path(..., ge=1, description="معرف المنتج"),
    data: ProductAvailabilityUpdate,
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    تحديث حالة توفر المنتج.
    
    Args:
        product_id: معرف المنتج
        data: بيانات التحديث
        service: خدمة المنتجات
        
    Returns:
        ProductResponse: المنتج المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على المنتج
    """
    logger.info(
        "api_update_product_availability",
        extra={
            "product_id": product_id,
            "is_available": data.is_available,
        },
    )

    try:
        product = await service.update_availability(
            product_id=product_id,
            availability_data=data,
        )
        return product

    except NotFoundError as e:
        logger.warning(
            "api_product_not_found_for_availability",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_product_availability_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث حالة توفر المنتج",
        )


# ==============================================
# ENABLE PRODUCT
# ==============================================

@router.post(
    "/{product_id}/enable",
    response_model=ProductResponse,
    summary="تفعيل منتج",
    description="تفعيل منتج (تعيين is_available = true)",
)
async def enable_product(
    *,
    product_id: int = Path(..., ge=1, description="معرف المنتج"),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    تفعيل منتج.
    
    Args:
        product_id: معرف المنتج
        service: خدمة المنتجات
        
    Returns:
        ProductResponse: المنتج المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على المنتج
    """
    logger.info(
        "api_enable_product",
        extra={"product_id": product_id},
    )

    try:
        product = await service.enable_product(
            product_id=product_id,
        )
        return product

    except NotFoundError as e:
        logger.warning(
            "api_product_not_found_for_enable",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_enable_product_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تفعيل المنتج",
        )


# ==============================================
# DISABLE PRODUCT
# ==============================================

@router.post(
    "/{product_id}/disable",
    response_model=ProductResponse,
    summary="إلغاء تفعيل منتج",
    description="إلغاء تفعيل منتج (تعيين is_available = false)",
)
async def disable_product(
    *,
    product_id: int = Path(..., ge=1, description="معرف المنتج"),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    إلغاء تفعيل منتج.
    
    Args:
        product_id: معرف المنتج
        service: خدمة المنتجات
        
    Returns:
        ProductResponse: المنتج المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على المنتج
    """
    logger.info(
        "api_disable_product",
        extra={"product_id": product_id},
    )

    try:
        product = await service.disable_product(
            product_id=product_id,
        )
        return product

    except NotFoundError as e:
        logger.warning(
            "api_product_not_found_for_disable",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_disable_product_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إلغاء تفعيل المنتج",
        )


# ==============================================
# DELETE PRODUCT
# ==============================================

@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف منتج",
    description="حذف منتج موجود",
)
async def delete_product(
    *,
    product_id: int = Path(..., ge=1, description="معرف المنتج"),
    service: ProductService = Depends(get_product_service),
) -> None:
    """
    حذف منتج.
    
    Args:
        product_id: معرف المنتج
        service: خدمة المنتجات
        
    Raises:
        HTTPException: إذا لم يتم العثور على المنتج أو كان مرتبطاً بطلبات
    """
    logger.info(
        "api_delete_product",
        extra={"product_id": product_id},
    )

    try:
        await service.delete_product(product_id=product_id)

    except NotFoundError as e:
        logger.warning(
            "api_product_not_found_for_delete",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_delete_product_validation_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_product_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف المنتج",
        )

    logger.info(
        "api_product_deleted_successfully",
        extra={"product_id": product_id},
    )


# ==============================================
# GET PRODUCT SUMMARY
# ==============================================

@router.get(
    "/stats/summary",
    response_model=ProductSummary,
    summary="ملخص المنتجات",
    description="الحصول على ملخص المنتجات لمطعم معين",
)
async def get_product_summary(
    *,
    restaurant_id: int = Query(
        ...,
        description="معرف المطعم",
        ge=1,
    ),
    service: ProductService = Depends(get_product_service),
) -> ProductSummary:
    """
    الحصول على ملخص المنتجات.
    
    Args:
        restaurant_id: معرف المطعم
        service: خدمة المنتجات
        
    Returns:
        ProductSummary: ملخص المنتجات
        
    Raises:
        HTTPException: إذا حدث خطأ
    """
    logger.info(
        "api_get_product_summary",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        summary = await service.get_product_summary(
            restaurant_id=restaurant_id,
        )
        return summary

    except Exception as e:
        logger.exception(
            "api_get_product_summary_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب ملخص المنتجات",
        )


# ==============================================
# GET RESTAURANT PRODUCTS
# ==============================================

@router.get(
    "/restaurant/{restaurant_id",
    response_model=ProductListResponse,
    summary="منتجات المطعم",
    description="الحصول على منتجات مطعم معين",
)
async def get_restaurant_products(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    only_available: bool = Query(
        True,
        description="جلب المنتجات المتاحة فقط",
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
    service: ProductService = Depends(get_product_service),
) -> ProductListResponse:
    """
    الحصول على منتجات مطعم معين.
    
    Args:
        restaurant_id: معرف المطعم
        only_available: جلب المنتجات المتاحة فقط
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة المنتجات
        
    Returns:
        ProductListResponse: قائمة المنتجات مع الإحصائيات
    """
    logger.info(
        "api_get_restaurant_products",
        extra={
            "restaurant_id": restaurant_id,
            "only_available": only_available,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        result = await service.get_by_restaurant(
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
            only_available=only_available,
        )
        return result

    except Exception as e:
        logger.exception(
            "api_get_restaurant_products_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب منتجات المطعم",
        )


# ==============================================
# GET CATEGORY PRODUCTS
# ==============================================

@router.get(
    "/category/{category_id}",
    response_model=ProductListResponse,
    summary="منتجات التصنيف",
    description="الحصول على منتجات تصنيف معين",
)
async def get_category_products(
    *,
    category_id: int = Path(..., ge=1, description="معرف التصنيف"),
    only_available: bool = Query(
        True,
        description="جلب المنتجات المتاحة فقط",
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
    service: ProductService = Depends(get_product_service),
) -> ProductListResponse:
    """
    الحصول على منتجات تصنيف معين.
    
    Args:
        category_id: معرف التصنيف
        only_available: جلب المنتجات المتاحة فقط
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة المنتجات
        
    Returns:
        ProductListResponse: قائمة المنتجات مع الإحصائيات
    """
    logger.info(
        "api_get_category_products",
        extra={
            "category_id": category_id,
            "only_available": only_available,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        result = await service.get_by_category(
            category_id=category_id,
            skip=skip,
            limit=limit,
            only_available=only_available,
        )
        return result

    except Exception as e:
        logger.exception(
            "api_get_category_products_error",
            extra={
                "category_id": category_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب منتجات التصنيف",
        )


# ==============================================
# GET PRODUCT WITH DETAILS
# ==============================================

@router.get(
    "/{product_id}/details",
    response_model=ProductResponse,
    summary="منتج بالمعرف مع التفاصيل",
    description="الحصول على منتج محدد مع جميع علاقاته",
)
async def get_product_with_details(
    *,
    product_id: int = Path(..., ge=1, description="معرف المنتج"),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    الحصول على منتج محدد مع جميع علاقاته.
    
    Args:
        product_id: معرف المنتج
        service: خدمة المنتجات
        
    Returns:
        ProductResponse: المنتج المطلوب مع العلاقات
        
    Raises:
        HTTPException: إذا لم يتم العثور على المنتج
    """
    logger.info(
        "api_get_product_with_details",
        extra={"product_id": product_id},
    )

    try:
        product = await service.get_with_details(product_id=product_id)
        return ProductResponse.model_validate(product)

    except NotFoundError as e:
        logger.warning(
            "api_product_not_found_for_details",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_product_with_details_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب تفاصيل المنتج",
        )