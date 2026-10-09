# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 👤 OWNERS API
# نقاط نهاية API للمالكين
# تدير عمليات إنشاء واستعراض المالكين
# ==============================================

"""MoulAI operational module for owners.

Part of MoulAI Platform - Agent-as-a-Service.
"""

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
from app.schemas.owner import (
    OwnerCreate,
    OwnerResponse,
    OwnerUpdate,
    OwnerStatusUpdate,
    OwnerListResponse,
    OwnerStatistics,
)
from app.services.business.owner_service import OwnerService

# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/owners",
    tags=["Owners"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================


async def get_owner_service(
    session: AsyncSession = Depends(get_db),
) -> OwnerService:
    """
    الحصول على خدمة المالكين.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        OwnerService: مثيل من OwnerService
    """
    return OwnerService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# CREATE OWNER
# ==============================================


@router.post(
    "/",
    response_model=OwnerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء مالك",
    description="إنشاء مالك جديد",
)
async def create_owner(
    *,
    data: OwnerCreate,
    service: OwnerService = Depends(get_owner_service),
) -> OwnerResponse:
    """
    إنشاء مالك جديد.
    """
    logger.info(
        "api_create_owner",
        extra={
            "chat_id": data.chat_id,
            "full_name": data.full_name,
        },
    )

    try:
        owner = await service.create_owner(owner_data=data)
        return owner

    except ConflictError as e:
        logger.warning(
            "api_create_owner_conflict",
            extra={
                "chat_id": data.chat_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_owner_validation_error",
            extra={
                "chat_id": data.chat_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        # ✅ عرض تفاصيل الخطأ الحقيقي للتشخيص
        logger.exception(
            "api_create_owner_error",
            extra={
                "chat_id": data.chat_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        # ✅ إرجاع تفاصيل الخطأ الحقيقي مؤقتاً للتشخيص
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء إنشاء المالك: {type(e).__name__} - {str(e)}",
        )


# ==============================================
# GET OWNER BY ID
# ==============================================


@router.get(
    "/{owner_id}",
    response_model=OwnerResponse,
    summary="مالك بالمعرف",
    description="الحصول على مالك محدد",
)
async def get_owner(
    *,
    owner_id: int = Path(..., ge=1, description="معرف المالك"),
    service: OwnerService = Depends(get_owner_service),
) -> OwnerResponse:
    """
    الحصول على مالك بالمعرف.

    Args:
        owner_id: معرف المالك
        service: خدمة المالكين

    Returns:
        OwnerResponse: المالك المطلوب

    Raises:
        HTTPException: إذا لم يتم العثور على المالك
    """
    logger.info(
        "api_get_owner",
        extra={"owner_id": owner_id},
    )

    try:
        owner = await service.get_owner_by_id(
            owner_id=owner_id,
        )
        return owner

    except NotFoundError as e:
        logger.warning(
            "api_owner_not_found",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_owner_error",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب المالك",
        )


# ==============================================
# GET OWNER BY CHAT ID
# ==============================================


@router.get(
    "/chat/{chat_id}",
    response_model=OwnerResponse,
    summary="مالك بمعرف الدردشة",
    description="الحصول على مالك بواسطة chat_id",
)
async def get_owner_by_chat_id(
    *,
    chat_id: int = Path(..., ge=1, description="معرف الدردشة في Telegram"),
    service: OwnerService = Depends(get_owner_service),
) -> OwnerResponse:
    """
    الحصول على مالك بواسطة chat_id.

    Args:
        chat_id: معرف الدردشة في Telegram
        service: خدمة المالكين

    Returns:
        OwnerResponse: المالك المطلوب

    Raises:
        HTTPException: إذا لم يتم العثور على المالك
    """
    logger.info(
        "api_get_owner_by_chat_id",
        extra={"chat_id": chat_id},
    )

    try:
        owner = await service.get_owner_by_chat_id(
            chat_id=chat_id,
        )

        if not owner:
            raise NotFoundError(
                message=f"المالك بـ chat_id '{chat_id}' غير موجود",
            )

        return owner

    except NotFoundError as e:
        logger.warning(
            "api_owner_not_found_by_chat_id",
            extra={
                "chat_id": chat_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_owner_by_chat_id_error",
            extra={
                "chat_id": chat_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب المالك",
        )


# ==============================================
# LIST OWNERS
# ==============================================


@router.get(
    "/",
    response_model=OwnerListResponse,
    summary="قائمة المالكين",
    description="الحصول على قائمة المالكين مع إمكانية التصفية",
)
async def list_owners(
    *,
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
    only_approved: bool = Query(
        False,
        description="جلب المالكين المعتمدين فقط",
    ),
    service: OwnerService = Depends(get_owner_service),
) -> OwnerListResponse:
    """
    الحصول على قائمة المالكين.

    Args:
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        only_approved: جلب المالكين المعتمدين فقط
        service: خدمة المالكين

    Returns:
        OwnerListResponse: قائمة المالكين مع الإحصائيات
    """
    logger.info(
        "api_list_owners",
        extra={
            "skip": skip,
            "limit": limit,
            "only_approved": only_approved,
        },
    )

    try:
        owners = await service.get_all_owners(
            skip=skip,
            limit=limit,
            only_approved=only_approved,
        )

        total = await service.count_owners()

        return OwnerListResponse(
            items=owners,
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_list_owners_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة المالكين",
        )


# ==============================================
# GET OWNERS BY STATUS
# ==============================================


@router.get(
    "/status/{status}",
    response_model=OwnerListResponse,
    summary="المالكين حسب الحالة",
    description="الحصول على المالكين حسب حالة التسجيل",
)
async def get_owners_by_status(
    *,
    status: str = Path(..., description="حالة التسجيل (pending, approved, rejected)"),
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
    service: OwnerService = Depends(get_owner_service),
) -> OwnerListResponse:
    """
    الحصول على المالكين حسب حالة التسجيل.

    Args:
        status: حالة التسجيل
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة المالكين

    Returns:
        OwnerListResponse: قائمة المالكين مع الإحصائيات

    Raises:
        HTTPException: إذا كانت الحالة غير صالحة
    """
    logger.info(
        "api_get_owners_by_status",
        extra={
            "status": status,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        owners = await service.get_owners_by_status(
            status=status,
            skip=skip,
            limit=limit,
        )

        total = await service.count_owners(status=status)

        return OwnerListResponse(
            items=owners,
            total=total,
            skip=skip,
            limit=limit,
        )

    except ValidationError as e:
        logger.warning(
            "api_get_owners_by_status_validation_error",
            extra={
                "status": status,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_owners_by_status_error",
            extra={
                "status": status,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب المالكين حسب الحالة",
        )


# ==============================================
# SEARCH OWNERS
# ==============================================


@router.get(
    "/search",
    response_model=OwnerListResponse,
    summary="بحث عن المالكين",
    description="البحث عن المالكين بالاسم أو رقم الهاتف",
)
async def search_owners(
    *,
    query: str = Query(
        ...,
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
    service: OwnerService = Depends(get_owner_service),
) -> OwnerListResponse:
    """
    البحث عن المالكين.

    Args:
        query: نص البحث
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة المالكين

    Returns:
        OwnerListResponse: قائمة المالكين مع الإحصائيات
    """
    logger.info(
        "api_search_owners",
        extra={
            "query": query,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        owners = await service.search_owners(
            query=query,
            skip=skip,
            limit=limit,
        )

        total = len(owners)

        return OwnerListResponse(
            items=owners,
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_search_owners_error",
            extra={
                "query": query,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء البحث عن المالكين",
        )


# ==============================================
# UPDATE OWNER
# ==============================================


@router.patch(
    "/{owner_id}",
    response_model=OwnerResponse,
    summary="تحديث مالك",
    description="تحديث مالك موجود",
)
async def update_owner(
    *,
    owner_id: int = Path(..., ge=1, description="معرف المالك"),
    data: OwnerUpdate,
    service: OwnerService = Depends(get_owner_service),
) -> OwnerResponse:
    """
    تحديث مالك موجود.

    Args:
        owner_id: معرف المالك
        data: بيانات التحديث
        service: خدمة المالكين

    Returns:
        OwnerResponse: المالك المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على المالك أو حدث تعارض
    """
    logger.info(
        "api_update_owner",
        extra={
            "owner_id": owner_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        owner = await service.update_owner(
            owner_id=owner_id,
            update_data=data,
        )
        return owner

    except NotFoundError as e:
        logger.warning(
            "api_owner_not_found_for_update",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_update_owner_conflict",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_owner_validation_error",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_owner_error",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث المالك",
        )


# ==============================================
# UPDATE OWNER STATUS
# ==============================================


@router.patch(
    "/{owner_id}/status",
    response_model=OwnerResponse,
    summary="تحديث حالة المالك",
    description="تحديث حالة تسجيل المالك",
)
async def update_owner_status(
    *,
    owner_id: int = Path(..., ge=1, description="معرف المالك"),
    data: OwnerStatusUpdate,
    service: OwnerService = Depends(get_owner_service),
) -> OwnerResponse:
    """
    تحديث حالة تسجيل المالك.

    Args:
        owner_id: معرف المالك
        data: بيانات تحديث الحالة
        service: خدمة المالكين

    Returns:
        OwnerResponse: المالك المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على المالك أو كانت الحالة غير صالحة
    """
    logger.info(
        "api_update_owner_status",
        extra={
            "owner_id": owner_id,
            "status": data.registration_status,
        },
    )

    try:
        owner = await service.update_owner_status(
            owner_id=owner_id,
            status_data=data,
        )
        return owner

    except NotFoundError as e:
        logger.warning(
            "api_owner_not_found_for_status_update",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_owner_status_validation_error",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_owner_status_error",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث حالة المالك",
        )


# ==============================================
# APPROVE OWNER
# ==============================================


@router.post(
    "/{owner_id}/approve",
    response_model=OwnerResponse,
    summary="اعتماد مالك",
    description="اعتماد مالك (تعيين الحالة إلى approved)",
)
async def approve_owner(
    *,
    owner_id: int = Path(..., ge=1, description="معرف المالك"),
    service: OwnerService = Depends(get_owner_service),
) -> OwnerResponse:
    """
    اعتماد مالك.

    Args:
        owner_id: معرف المالك
        service: خدمة المالكين

    Returns:
        OwnerResponse: المالك المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على المالك
    """
    logger.info(
        "api_approve_owner",
        extra={"owner_id": owner_id},
    )

    try:
        owner = await service.approve_owner(
            owner_id=owner_id,
        )
        return owner

    except NotFoundError as e:
        logger.warning(
            "api_owner_not_found_for_approve",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_approve_owner_error",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء اعتماد المالك",
        )


# ==============================================
# REJECT OWNER
# ==============================================


@router.post(
    "/{owner_id}/reject",
    response_model=OwnerResponse,
    summary="رفض مالك",
    description="رفض مالك (تعيين الحالة إلى rejected)",
)
async def reject_owner(
    *,
    owner_id: int = Path(..., ge=1, description="معرف المالك"),
    service: OwnerService = Depends(get_owner_service),
) -> OwnerResponse:
    """
    رفض مالك.

    Args:
        owner_id: معرف المالك
        service: خدمة المالكين

    Returns:
        OwnerResponse: المالك المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على المالك
    """
    logger.info(
        "api_reject_owner",
        extra={"owner_id": owner_id},
    )

    try:
        owner = await service.reject_owner(
            owner_id=owner_id,
        )
        return owner

    except NotFoundError as e:
        logger.warning(
            "api_owner_not_found_for_reject",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_reject_owner_error",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء رفض المالك",
        )


# ==============================================
# DELETE OWNER
# ==============================================


@router.delete(
    "/{owner_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف مالك",
    description="حذف مالك موجود",
)
async def delete_owner(
    *,
    owner_id: int = Path(..., ge=1, description="معرف المالك"),
    service: OwnerService = Depends(get_owner_service),
) -> None:
    """
    حذف مالك.

    Args:
        owner_id: معرف المالك
        service: خدمة المالكين

    Raises:
        HTTPException: إذا لم يتم العثور على المالك أو كان لديه مطاعم
    """
    logger.info(
        "api_delete_owner",
        extra={"owner_id": owner_id},
    )

    try:
        await service.delete_owner(
            owner_id=owner_id,
        )

    except NotFoundError as e:
        logger.warning(
            "api_owner_not_found_for_delete",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_delete_owner_validation_error",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_owner_error",
            extra={
                "owner_id": owner_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف المالك",
        )

    logger.info(
        "api_owner_deleted_successfully",
        extra={"owner_id": owner_id},
    )


# ==============================================
# GET OWNER STATISTICS
# ==============================================


@router.get(
    "/stats",
    response_model=OwnerStatistics,
    summary="إحصائيات المالكين",
    description="الحصول على إحصائيات المالكين",
)
async def get_owner_statistics(
    *,
    service: OwnerService = Depends(get_owner_service),
) -> OwnerStatistics:
    """
    الحصول على إحصائيات المالكين.

    Args:
        service: خدمة المالكين

    Returns:
        OwnerStatistics: إحصائيات المالكين
    """
    logger.info("api_get_owner_statistics")

    try:
        stats = await service.get_owner_statistics()

        return OwnerStatistics(
            total=stats["total"],
            pending=stats["pending"],
            approved=stats["approved"],
            rejected=stats["rejected"],
            trial_used=0,  # TODO: سيتم حسابها لاحقاً
            trial_available=stats["total"],  # TODO: سيتم حسابها لاحقاً
        )

    except Exception as e:
        logger.exception(
            "api_get_owner_statistics_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب إحصائيات المالكين",
        )
