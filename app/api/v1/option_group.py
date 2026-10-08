# ==============================================
# 🎛 OPTION GROUPS API
# نقاط نهاية API لمجموعات الخيارات
# تدير عمليات إنشاء واستعراض وتحديث وحذف مجموعات الخيارات
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
from app.schemas.option_group import (
    OptionGroupCreate,
    OptionGroupResponse,
    OptionGroupSummary,
    OptionGroupUpdate,
    OptionGroupWithOptionsResponse,
    OptionGroupListResponse,
)
from app.services.business.option_groups_service import OptionGroupsService
from app.services.business.product_service import ProductService

# ==============================================
# 🧩 TYPES
# ==============================================

OptionGroupList = List[OptionGroupResponse]


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/option-groups",
    tags=["Option Groups"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================

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
# LIST OPTION GROUPS
# ==============================================

@router.get(
    "/",
    response_model=OptionGroupListResponse,
    summary="قائمة مجموعات الخيارات",
    description="الحصول على قائمة مجموعات الخيارات مع إمكانية التصفية",
)
async def list_option_groups(
    *,
    product_id: Optional[int] = Query(
        None,
        description="معرف المنتج",
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
    service: OptionGroupsService = Depends(get_option_groups_service),
) -> OptionGroupListResponse:
    """
    الحصول على قائمة مجموعات الخيارات.
    
    Args:
        product_id: معرف المنتج للتصفية
        search: نص البحث
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة مجموعات الخيارات
        
    Returns:
        OptionGroupListResponse: قائمة مجموعات الخيارات مع الإحصائيات
    """
    logger.info(
        "api_list_option_groups",
        extra={
            "product_id": product_id,
            "search": search,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        if search is not None:
            groups = await service.search(
                query=search,
                product_id=product_id,
                skip=skip,
                limit=limit,
            )
            total = len(groups)
        elif product_id is not None:
            groups = await service.get_by_product(
                product_id=product_id,
                skip=skip,
                limit=limit,
            )
            total = await service.count_by_product(product_id=product_id)
        else:
            # جلب جميع المجموعات
            groups = await service.repo.get_all(
                skip=skip,
                limit=limit,
                order_by="sort_order",
            )
            total = await service.repo.count()

        return OptionGroupListResponse(
            items=groups,
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_list_option_groups_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة مجموعات الخيارات",
        )


# ==============================================
# GET OPTION GROUP BY ID
# ==============================================

@router.get(
    "/{group_id}",
    response_model=OptionGroupWithOptionsResponse,
    summary="مجموعة خيارات بالمعرف",
    description="الحصول على مجموعة خيارات محددة مع خياراتها",
)
async def get_option_group(
    *,
    group_id: int = Path(..., ge=1, description="معرف مجموعة الخيارات"),
    service: OptionGroupsService = Depends(get_option_groups_service),
) -> OptionGroupWithOptionsResponse:
    """
    الحصول على مجموعة خيارات محددة مع خياراتها.
    
    Args:
        group_id: معرف مجموعة الخيارات
        service: خدمة مجموعات الخيارات
        
    Returns:
        OptionGroupWithOptionsResponse: مجموعة الخيارات مع خياراتها
        
    Raises:
        HTTPException: إذا لم يتم العثور على المجموعة
    """
    logger.info(
        "api_get_option_group",
        extra={"group_id": group_id},
    )

    try:
        group = await service.get_with_options(
            group_id=group_id,
        )
        return group

    except NotFoundError as e:
        logger.warning(
            "api_option_group_not_found",
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
            "api_get_option_group_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب مجموعة الخيارات",
        )


# ==============================================
# GET PRODUCT OPTION GROUPS
# ==============================================

@router.get(
    "/product/{product_id}",
    response_model=OptionGroupListResponse,
    summary="مجموعات خيارات المنتج",
    description="الحصول على مجموعات خيارات منتج معين",
)
async def get_product_option_groups(
    *,
    product_id: int = Path(..., ge=1, description="معرف المنتج"),
    only_required: bool = Query(
        False,
        description="جلب المجموعات الإجبارية فقط",
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
    service: OptionGroupsService = Depends(get_option_groups_service),
) -> OptionGroupListResponse:
    """
    الحصول على مجموعات خيارات منتج معين.
    
    Args:
        product_id: معرف المنتج
        only_required: جلب المجموعات الإجبارية فقط
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة مجموعات الخيارات
        
    Returns:
        OptionGroupListResponse: قائمة مجموعات الخيارات مع الإحصائيات
    """
    logger.info(
        "api_get_product_option_groups",
        extra={
            "product_id": product_id,
            "only_required": only_required,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        if only_required:
            groups = await service.get_required_by_product(
                product_id=product_id,
            )
            total = len(groups)
        else:
            groups = await service.get_by_product(
                product_id=product_id,
                skip=skip,
                limit=limit,
            )
            total = await service.count_by_product(product_id=product_id)

        return OptionGroupListResponse(
            items=groups,
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_get_product_option_groups_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب مجموعات خيارات المنتج",
        )


# ==============================================
# CREATE OPTION GROUP
# ==============================================

@router.post(
    "/",
    response_model=OptionGroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء مجموعة خيارات",
    description="إنشاء مجموعة خيارات جديدة",
)
async def create_option_group(
    *,
    data: OptionGroupCreate,
    product_id: int = Query(
        ...,
        description="معرف المنتج",
        ge=1,
    ),
    service: OptionGroupsService = Depends(get_option_groups_service),
) -> OptionGroupResponse:
    """
    إنشاء مجموعة خيارات جديدة.
    
    Args:
        data: بيانات مجموعة الخيارات
        product_id: معرف المنتج
        service: خدمة مجموعات الخيارات
        
    Returns:
        OptionGroupResponse: مجموعة الخيارات المنشأة
        
    Raises:
        HTTPException: إذا حدث خطأ أثناء الإنشاء
    """
    logger.info(
        "api_create_option_group",
        extra={
            "product_id": product_id,
            "option_group_name": data.name,
        },
    )

    try:
        # إضافة product_id إلى البيانات
        data.product_id = product_id
        group = await service.create_group(
            group_data=data,
        )
        return group

    except NotFoundError as e:
        logger.warning(
            "api_create_option_group_product_not_found",
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
            "api_create_option_group_conflict",
            extra={
                "product_id": product_id,
                "option_group_name": data.name,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_option_group_validation_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_option_group_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء مجموعة الخيارات",
        )


# ==============================================
# UPDATE OPTION GROUP
# ==============================================

@router.patch(
    "/{group_id}",
    response_model=OptionGroupResponse,
    summary="تحديث مجموعة خيارات",
    description="تحديث مجموعة خيارات موجودة",
)
async def update_option_group(
    *,
    group_id: int = Path(..., ge=1, description="معرف مجموعة الخيارات"),
    data: OptionGroupUpdate,
    service: OptionGroupsService = Depends(get_option_groups_service),
) -> OptionGroupResponse:
    """
    تحديث مجموعة خيارات موجودة.
    
    Args:
        group_id: معرف مجموعة الخيارات
        data: بيانات التحديث
        service: خدمة مجموعات الخيارات
        
    Returns:
        OptionGroupResponse: مجموعة الخيارات المحدثة
        
    Raises:
        HTTPException: إذا لم يتم العثور على المجموعة أو حدث تعارض
    """
    logger.info(
        "api_update_option_group",
        extra={
            "group_id": group_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        group = await service.update_group(
            group_id=group_id,
            update_data=data,
        )
        return group

    except NotFoundError as e:
        logger.warning(
            "api_option_group_not_found_for_update",
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
            "api_update_option_group_conflict",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_option_group_validation_error",
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
            "api_update_option_group_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث مجموعة الخيارات",
        )


# ==============================================
# UPDATE OPTION GROUP SORT ORDER
# ==============================================

@router.patch(
    "/{group_id}/sort-order",
    response_model=OptionGroupResponse,
    summary="تحديث ترتيب مجموعة الخيارات",
    description="تحديث ترتيب مجموعة الخيارات",
)
async def update_option_group_sort_order(
    *,
    group_id: int = Path(..., ge=1, description="معرف مجموعة الخيارات"),
    sort_order: int = Query(
        ...,
        ge=0,
        description="الترتيب الجديد",
    ),
    service: OptionGroupsService = Depends(get_option_groups_service),
) -> OptionGroupResponse:
    """
    تحديث ترتيب مجموعة الخيارات.
    
    Args:
        group_id: معرف مجموعة الخيارات
        sort_order: الترتيب الجديد
        service: خدمة مجموعات الخيارات
        
    Returns:
        OptionGroupResponse: مجموعة الخيارات المحدثة
        
    Raises:
        HTTPException: إذا لم يتم العثور على المجموعة
    """
    logger.info(
        "api_update_option_group_sort_order",
        extra={
            "group_id": group_id,
            "sort_order": sort_order,
        },
    )

    try:
        group = await service.update_sort_order(
            group_id=group_id,
            sort_order=sort_order,
        )
        return group

    except NotFoundError as e:
        logger.warning(
            "api_option_group_not_found_for_sort_order",
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
            "api_update_option_group_sort_order_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث ترتيب مجموعة الخيارات",
        )


# ==============================================
# UPDATE OPTION GROUP REQUIRED
# ==============================================

@router.patch(
    "/{group_id}/required",
    response_model=OptionGroupResponse,
    summary="تحديث حالة الإجبار",
    description="تحديث حالة الإجبار لمجموعة الخيارات",
)
async def update_option_group_required(
    *,
    group_id: int = Path(..., ge=1, description="معرف مجموعة الخيارات"),
    required: bool = Query(
        ...,
        description="حالة الإجبار الجديدة",
    ),
    service: OptionGroupsService = Depends(get_option_groups_service),
) -> OptionGroupResponse:
    """
    تحديث حالة الإجبار لمجموعة الخيارات.
    
    Args:
        group_id: معرف مجموعة الخيارات
        required: حالة الإجبار الجديدة
        service: خدمة مجموعات الخيارات
        
    Returns:
        OptionGroupResponse: مجموعة الخيارات المحدثة
        
    Raises:
        HTTPException: إذا لم يتم العثور على المجموعة
    """
    logger.info(
        "api_update_option_group_required",
        extra={
            "group_id": group_id,
            "required": required,
        },
    )

    try:
        group = await service.update_required(
            group_id=group_id,
            required=required,
        )
        return group

    except NotFoundError as e:
        logger.warning(
            "api_option_group_not_found_for_required",
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
            "api_update_option_group_required_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث حالة الإجبار",
        )


# ==============================================
# UPDATE OPTION GROUP MULTIPLE CHOICE
# ==============================================

@router.patch(
    "/{group_id}/multiple-choice",
    response_model=OptionGroupResponse,
    summary="تحديث حالة الاختيار المتعدد",
    description="تحديث حالة الاختيار المتعدد لمجموعة الخيارات",
)
async def update_option_group_multiple_choice(
    *,
    group_id: int = Path(..., ge=1, description="معرف مجموعة الخيارات"),
    multiple_choice: bool = Query(
        ...,
        description="حالة الاختيار المتعدد الجديدة",
    ),
    service: OptionGroupsService = Depends(get_option_groups_service),
) -> OptionGroupResponse:
    """
    تحديث حالة الاختيار المتعدد لمجموعة الخيارات.
    
    Args:
        group_id: معرف مجموعة الخيارات
        multiple_choice: حالة الاختيار المتعدد الجديدة
        service: خدمة مجموعات الخيارات
        
    Returns:
        OptionGroupResponse: مجموعة الخيارات المحدثة
        
    Raises:
        HTTPException: إذا لم يتم العثور على المجموعة
    """
    logger.info(
        "api_update_option_group_multiple_choice",
        extra={
            "group_id": group_id,
            "multiple_choice": multiple_choice,
        },
    )

    try:
        group = await service.update_multiple_choice(
            group_id=group_id,
            multiple_choice=multiple_choice,
        )
        return group

    except NotFoundError as e:
        logger.warning(
            "api_option_group_not_found_for_multiple_choice",
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
            "api_update_option_group_multiple_choice_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث حالة الاختيار المتعدد",
        )


# ==============================================
# REORDER OPTION GROUPS
# ==============================================

@router.post(
    "/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="إعادة ترتيب مجموعات الخيارات",
    description="إعادة ترتيب مجموعات الخيارات حسب القائمة المقدمة",
)
async def reorder_option_groups(
    *,
    product_id: int = Query(
        ...,
        description="معرف المنتج",
        ge=1,
    ),
    group_order: List[int] = Query(
        ...,
        description="قائمة معرفات المجموعات بالترتيب الجديد",
    ),
    service: OptionGroupsService = Depends(get_option_groups_service),
) -> None:
    """
    إعادة ترتيب مجموعات الخيارات.
    
    Args:
        product_id: معرف المنتج
        group_order: قائمة معرفات المجموعات بالترتيب الجديد
        service: خدمة مجموعات الخيارات
        
    Raises:
        HTTPException: إذا حدث خطأ
    """
    logger.info(
        "api_reorder_option_groups",
        extra={
            "product_id": product_id,
            "group_count": len(group_order),
        },
    )

    try:
        await service.reorder_groups(
            product_id=product_id,
            group_order=group_order,
        )

    except NotFoundError as e:
        logger.warning(
            "api_reorder_option_groups_not_found",
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
            "api_reorder_option_groups_validation_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_reorder_option_groups_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إعادة ترتيب مجموعات الخيارات",
        )


# ==============================================
# DELETE OPTION GROUP
# ==============================================

@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف مجموعة خيارات",
    description="حذف مجموعة خيارات موجودة",
)
async def delete_option_group(
    *,
    group_id: int = Path(..., ge=1, description="معرف مجموعة الخيارات"),
    service: OptionGroupsService = Depends(get_option_groups_service),
) -> None:
    """
    حذف مجموعة خيارات موجودة.
    
    Args:
        group_id: معرف مجموعة الخيارات
        service: خدمة مجموعات الخيارات
        
    Raises:
        HTTPException: إذا لم يتم العثور على المجموعة أو كانت تحتوي على خيارات
    """
    logger.info(
        "api_delete_option_group",
        extra={"group_id": group_id},
    )

    try:
        await service.delete_group(
            group_id=group_id,
        )

    except NotFoundError as e:
        logger.warning(
            "api_option_group_not_found_for_delete",
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
            "api_delete_option_group_validation_error",
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
            "api_delete_option_group_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف مجموعة الخيارات",
        )

    logger.info(
        "api_option_group_deleted_successfully",
        extra={"group_id": group_id},
    )


# ==============================================
# DELETE PRODUCT OPTION GROUPS
# ==============================================

@router.delete(
    "/product/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف جميع مجموعات خيارات المنتج",
    description="حذف جميع مجموعات خيارات منتج معين",
)
async def delete_product_option_groups(
    *,
    product_id: int = Path(..., ge=1, description="معرف المنتج"),
    service: OptionGroupsService = Depends(get_option_groups_service),
) -> None:
    """
    حذف جميع مجموعات خيارات منتج معين.
    
    Args:
        product_id: معرف المنتج
        service: خدمة مجموعات الخيارات
        
    Raises:
        HTTPException: إذا لم يتم العثور على المنتج
    """
    logger.info(
        "api_delete_product_option_groups",
        extra={"product_id": product_id},
    )

    try:
        await service.delete_by_product(
            product_id=product_id,
        )

    except NotFoundError as e:
        logger.warning(
            "api_product_not_found_for_option_groups_delete",
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
            "api_delete_product_option_groups_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف مجموعات خيارات المنتج",
        )

    logger.info(
        "api_product_option_groups_deleted_successfully",
        extra={"product_id": product_id},
    )


# ==============================================
# GET OPTION GROUPS SUMMARY
# ==============================================

@router.get(
    "/product/{product_id}/summary",
    response_model=OptionGroupSummary,
    summary="ملخص مجموعات خيارات المنتج",
    description="الحصول على ملخص مجموعات خيارات منتج معين",
)
async def get_option_groups_summary(
    *,
    product_id: int = Path(..., ge=1, description="معرف المنتج"),
    service: OptionGroupsService = Depends(get_option_groups_service),
) -> OptionGroupSummary:
    """
    الحصول على ملخص مجموعات خيارات منتج معين.
    
    Args:
        product_id: معرف المنتج
        service: خدمة مجموعات الخيارات
        
    Returns:
        OptionGroupSummary: ملخص مجموعات خيارات المنتج
        
    Raises:
        HTTPException: إذا حدث خطأ
    """
    logger.info(
        "api_get_option_groups_summary",
        extra={"product_id": product_id},
    )

    try:
        summary = await service.get_option_group_summary(
            product_id=product_id,
        )
        return summary

    except Exception as e:
        logger.exception(
            "api_get_option_groups_summary_error",
            extra={
                "product_id": product_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب ملخص مجموعات الخيارات",
        )