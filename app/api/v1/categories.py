# ==============================================
# 📂 CATEGORIES API
# نقاط نهاية API للتصنيفات
# تدير عمليات إنشاء واستعراض وتحديث وحذف التصنيفات
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
from app.schemas.categories import (
    CategoryCreate,
    CategoryResponse,
    CategorySummary,
    CategoryUpdate,
    CategoryListResponse,
)
from app.schemas.product import (
    ProductListResponse,
)
from app.services.business.category_service import CategoryService
from app.services.business.product_service import ProductService

# ==============================================
# 🧩 TYPES
# ==============================================

CategoryList = List[CategoryResponse]


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================

async def get_category_service(
    session: AsyncSession = Depends(get_db),
) -> CategoryService:
    """
    الحصول على خدمة التصنيفات.
    
    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        CategoryService: مثيل من CategoryService
    """
    return CategoryService(session)


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
# LIST CATEGORIES
# ==============================================

@router.get(
    "/",
    response_model=CategoryListResponse,
    summary="قائمة التصنيفات",
    description="الحصول على قائمة التصنيفات مع إمكانية التصفية",
)
async def list_categories(
    *,
    restaurant_id: Optional[int] = Query(
        None,
        description="معرف المطعم",
        ge=1,
    ),
    search: Optional[str] = Query(
        None,
        min_length=1,
        max_length=255,
        description="نص البحث",
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
    service: CategoryService = Depends(get_category_service),
) -> CategoryListResponse:
    """
    الحصول على قائمة التصنيفات.
    
    Args:
        restaurant_id: معرف المطعم للتصفية
        search: نص البحث
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة التصنيفات
        
    Returns:
        CategoryListResponse: قائمة التصنيفات مع الإحصائيات
    """
    logger.info(
        "api_list_categories",
        extra={
            "restaurant_id": restaurant_id,
            "search": search,
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
        elif restaurant_id is not None:
            result = await service.get_by_restaurant(
                restaurant_id=restaurant_id,
                skip=skip,
                limit=limit,
            )
        else:
            # جلب جميع التصنيفات
            categories = await service.repo.get_all(
                skip=skip,
                limit=limit,
                order_by="sort_order",
            )
            total = await service.repo.count()
            
            result = CategoryListResponse(
                items=[CategoryResponse.model_validate(c) for c in categories],
                total=total,
                skip=skip,
                limit=limit,
            )

        return result

    except Exception as e:
        logger.exception(
            "api_list_categories_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة التصنيفات",
        )


# ==============================================
# GET CATEGORY BY ID
# ==============================================

@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="تصنيف بالمعرف",
    description="الحصول على تصنيف محدد",
)
async def get_category(
    *,
    category_id: int = Path(..., ge=1, description="معرف التصنيف"),
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """
    الحصول على تصنيف بالمعرف.
    
    Args:
        category_id: معرف التصنيف
        service: خدمة التصنيفات
        
    Returns:
        CategoryResponse: التصنيف المطلوب
        
    Raises:
        HTTPException: إذا لم يتم العثور على التصنيف
    """
    logger.info(
        "api_get_category",
        extra={"category_id": category_id},
    )

    try:
        category = await service.get_by_id(category_id=category_id)
        return category

    except NotFoundError as e:
        logger.warning(
            "api_category_not_found",
            extra={
                "category_id": category_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_category_error",
            extra={
                "category_id": category_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب التصنيف",
        )


# ==============================================
# CREATE CATEGORY
# ==============================================

@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء تصنيف",
    description="إنشاء تصنيف جديد",
)
async def create_category(
    *,
    data: CategoryCreate,
    restaurant_id: int = Query(
        ...,
        description="معرف المطعم",
        ge=1,
    ),
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """
    إنشاء تصنيف جديد.
    
    Args:
        data: بيانات التصنيف
        restaurant_id: معرف المطعم
        service: خدمة التصنيفات
        
    Returns:
        CategoryResponse: التصنيف المنشأ
        
    Raises:
        HTTPException: إذا حدث خطأ أثناء الإنشاء
    """
    logger.info(
        "api_create_category",
        extra={
            "restaurant_id": restaurant_id,
            "categories_name": data.name,
        },
    )

    try:
        category = await service.create_category(
            restaurant_id=restaurant_id,
            category_data=data,
        )
        return category

    except ConflictError as e:
        logger.warning(
            "api_create_category_conflict",
            extra={
                "restaurant_id": restaurant_id,
                "categories_name": data.name,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_category_validation_error",
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
            "api_create_category_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء التصنيف",
        )


# ==============================================
# UPDATE CATEGORY
# ==============================================

@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="تحديث تصنيف",
    description="تحديث تصنيف موجود",
)
async def update_category(
    *,
    category_id: int = Path(..., ge=1, description="معرف التصنيف"),
    data: CategoryUpdate,
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """
    تحديث تصنيف موجود.
    
    Args:
        category_id: معرف التصنيف
        data: بيانات التحديث
        service: خدمة التصنيفات
        
    Returns:
        CategoryResponse: التصنيف المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على التصنيف أو حدث تعارض
    """
    logger.info(
        "api_update_category",
        extra={
            "category_id": category_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        category = await service.update_category(
            category_id=category_id,
            update_data=data,
        )
        return category

    except NotFoundError as e:
        logger.warning(
            "api_category_not_found_for_update",
            extra={
                "category_id": category_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_update_category_conflict",
            extra={
                "category_id": category_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_category_validation_error",
            extra={
                "category_id": category_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_category_error",
            extra={
                "category_id": category_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث التصنيف",
        )


# ==============================================
# REORDER CATEGORIES
# ==============================================

@router.post(
    "/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="إعادة ترتيب التصنيفات",
    description="إعادة ترتيب التصنيفات حسب القائمة المقدمة",
)
async def reorder_categories(
    *,
    restaurant_id: int = Query(
        ...,
        description="معرف المطعم",
        ge=1,
    ),
    category_order: List[int] = Query(
        ...,
        description="قائمة معرفات التصنيفات بالترتيب الجديد",
    ),
    service: CategoryService = Depends(get_category_service),
) -> None:
    """
    إعادة ترتيب التصنيفات.
    
    Args:
        restaurant_id: معرف المطعم
        category_order: قائمة معرفات التصنيفات بالترتيب الجديد
        service: خدمة التصنيفات
        
    Raises:
        HTTPException: إذا حدث خطأ
    """
    logger.info(
        "api_reorder_categories",
        extra={
            "restaurant_id": restaurant_id,
            "category_count": len(category_order),
        },
    )

    try:
        await service.reorder_categories(
            restaurant_id=restaurant_id,
            category_order=category_order,
        )

    except NotFoundError as e:
        logger.warning(
            "api_reorder_categories_not_found",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_reorder_categories_validation_error",
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
            "api_reorder_categories_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إعادة ترتيب التصنيفات",
        )


# ==============================================
# DELETE CATEGORY
# ==============================================

@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف تصنيف",
    description="حذف تصنيف موجود",
)
async def delete_category(
    *,
    category_id: int = Path(..., ge=1, description="معرف التصنيف"),
    service: CategoryService = Depends(get_category_service),
) -> None:
    """
    حذف تصنيف.
    
    Args:
        category_id: معرف التصنيف
        service: خدمة التصنيفات
        
    Raises:
        HTTPException: إذا لم يتم العثور على التصنيف أو كان يحتوي على منتجات
    """
    logger.info(
        "api_delete_category",
        extra={"category_id": category_id},
    )

    try:
        await service.delete_category(category_id=category_id)

    except NotFoundError as e:
        logger.warning(
            "api_category_not_found_for_delete",
            extra={
                "category_id": category_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_delete_category_validation_error",
            extra={
                "category_id": category_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_category_error",
            extra={
                "category_id": category_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف التصنيف",
        )

    logger.info(
        "api_category_deleted_successfully",
        extra={"category_id": category_id},
    )


# ==============================================
# GET CATEGORY SUMMARY
# ==============================================

@router.get(
    "/stats/summary",
    response_model=CategorySummary,
    summary="ملخص التصنيفات",
    description="الحصول على ملخص التصنيفات لمطعم معين",
)
async def get_category_summary(
    *,
    restaurant_id: int = Query(
        ...,
        description="معرف المطعم",
        ge=1,
    ),
    service: CategoryService = Depends(get_category_service),
    product_service: ProductService = Depends(get_product_service),
) -> CategorySummary:
    """
    الحصول على ملخص التصنيفات.
    
    Args:
        restaurant_id: معرف المطعم
        service: خدمة التصنيفات
        product_service: خدمة المنتجات
        
    Returns:
        CategorySummary: ملخص التصنيفات
    """
    logger.info(
        "api_get_category_summary",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        summary = await service.get_category_summary(
            restaurant_id=restaurant_id,
        )
        return summary

    except NotFoundError as e:
        logger.warning(
            "api_category_summary_not_found",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_category_summary_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب ملخص التصنيفات",
        )


# ==============================================
# GET RESTAURANT CATEGORIES
# ==============================================

@router.get(
    "/restaurant/{restaurant_id}",
    response_model=CategoryListResponse,
    summary="تصنيفات المطعم",
    description="الحصول على تصنيفات مطعم معين",
)
async def get_restaurant_categories(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
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
    service: CategoryService = Depends(get_category_service),
) -> CategoryListResponse:
    """
    الحصول على تصنيفات مطعم معين.
    
    Args:
        restaurant_id: معرف المطعم
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة التصنيفات
        
    Returns:
        CategoryListResponse: قائمة التصنيفات مع الإحصائيات
    """
    logger.info(
        "api_get_restaurant_categories",
        extra={
            "restaurant_id": restaurant_id,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        result = await service.get_by_restaurant(
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
        )
        return result

    except Exception as e:
        logger.exception(
            "api_get_restaurant_categories_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب تصنيفات المطعم",
        )


# ==============================================
# GET CATEGORY PRODUCTS
# ==============================================

@router.get(
    "/{category_id}/products",
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
    service: CategoryService = Depends(get_category_service),
    product_service: ProductService = Depends(get_product_service),
) -> ProductListResponse:
    """
    الحصول على منتجات تصنيف معين.
    
    Args:
        category_id: معرف التصنيف
        only_available: جلب المنتجات المتاحة فقط
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة التصنيفات
        product_service: خدمة المنتجات
        
    Returns:
        ProductListResponse: قائمة المنتجات مع الإحصائيات
        
    Raises:
        HTTPException: إذا لم يتم العثور على التصنيف
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
        # التحقق من وجود التصنيف
        await service.get_by_id(category_id=category_id)

        # جلب منتجات التصنيف
        result = await product_service.get_by_category(
            category_id=category_id,
            skip=skip,
            limit=limit,
            only_available=only_available,
        )
        return result

    except NotFoundError as e:
        logger.warning(
            "api_category_not_found_for_products",
            extra={
                "category_id": category_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
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