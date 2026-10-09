# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / API / V1 / BRANCHES
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for branches.

Part of MoulAI Platform - Agent-as-a-Service.
"""

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
    BranchLimitExceededError,
)

from app.core.database import get_db
from app.core.logger import logger
from app.schemas.branch import (
    BranchCreate,
    BranchResponse,
    BranchStatusUpdate,
    BranchSummary,
    BranchUpdate,
    BranchListResponse,
)
from app.services.business.branch_service import BranchService

# ==============================================
# 🧩 TYPES
# ==============================================

BranchCostResponse = dict


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/branches",
    tags=["Branches"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================


async def get_branch_service(
    session: AsyncSession = Depends(get_db),
) -> BranchService:
    """
    الحصول على خدمة الفروع.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        BranchService: مثيل من BranchService
    """
    return BranchService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# LIST BRANCHES
# ==============================================


@router.get(
    "/",
    response_model=BranchListResponse,
    summary="قائمة الفروع",
    description="الحصول على قائمة الفروع مع إمكانية التصفية",
)
async def list_branches(
    *,
    restaurant_id: Optional[int] = Query(
        None,
        description="معرف المطعم",
        ge=1,
    ),
    wilaya: Optional[str] = Query(
        None,
        max_length=100,
        description="الولاية",
    ),
    search: Optional[str] = Query(
        None,
        min_length=1,
        max_length=255,
        description="نص البحث",
    ),
    only_active: bool = Query(
        True,
        description="جلب الفروع النشطة فقط",
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
    service: BranchService = Depends(get_branch_service),
) -> BranchListResponse:
    """
    الحصول على قائمة الفروع.

    Args:
        restaurant_id: معرف المطعم للتصفية
        wilaya: الولاية للتصفية
        search: نص البحث
        only_active: جلب الفروع النشطة فقط
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة الفروع

    Returns:
        BranchListResponse: قائمة الفروع مع الإحصائيات
    """
    logger.info(
        "api_list_branches",
        extra={
            "restaurant_id": restaurant_id,
            "wilaya": wilaya,
            "search": search,
            "only_active": only_active,
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
                only_active=only_active,
            )
        elif wilaya is not None:
            # جلب الفروع حسب الولاية
            branches = await service.repo.get_by_wilaya(
                wilaya=wilaya,
                skip=skip,
                limit=limit,
                only_active=only_active,
            )
            total = await service.repo.count_by_wilaya(
                wilaya=wilaya,
                only_active=only_active,
            )
            result = BranchListResponse(
                items=[BranchResponse.model_validate(b) for b in branches],
                total=total,
                skip=skip,
                limit=limit,
            )
        else:
            # جلب جميع الفروع
            filters = {}
            if only_active:
                filters["is_active"] = True

            branches = await service.repo.get_all(
                skip=skip,
                limit=limit,
                filters=filters,
                order_by="name",
            )

            total = await service.repo.count(filters=filters)

            result = BranchListResponse(
                items=[BranchResponse.model_validate(b) for b in branches],
                total=total,
                skip=skip,
                limit=limit,
            )

        return result

    except NotFoundError as e:
        logger.warning(
            "api_list_branches_not_found",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_list_branches_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة الفروع",
        )


# ==============================================
# GET BRANCH BY ID
# ==============================================


@router.get(
    "/{branch_id}",
    response_model=BranchResponse,
    summary="فرع بالمعرف",
    description="الحصول على فرع محدد",
)
async def get_branch(
    *,
    branch_id: int = Path(..., ge=1, description="معرف الفرع"),
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """
    الحصول على فرع بالمعرف.

    Args:
        branch_id: معرف الفرع
        service: خدمة الفروع

    Returns:
        BranchResponse: الفرع المطلوب

    Raises:
        HTTPException: إذا لم يتم العثور على الفرع
    """
    logger.info(
        "api_get_branch",
        extra={"branch_id": branch_id},
    )

    try:
        branch = await service.get_by_id(branch_id=branch_id)
        return branch

    except NotFoundError as e:
        logger.warning(
            "api_branch_not_found",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_branch_error",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب الفرع",
        )


# ==============================================
# CREATE BRANCH
# ==============================================


@router.post(
    "/",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء فرع",
    description="إنشاء فرع جديد",
)
async def create_branch(
    *,
    data: BranchCreate,
    restaurant_id: int = Query(
        ...,
        description="معرف المطعم",
        ge=1,
    ),
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """
    إنشاء فرع جديد.

    Args:
        data: بيانات الفرع
        restaurant_id: معرف المطعم
        service: خدمة الفروع

    Returns:
        BranchResponse: الفرع المنشأ

    Raises:
        HTTPException: إذا حدث خطأ أثناء الإنشاء
    """
    logger.info(
        "api_create_branch",
        extra={
            "restaurant_id": restaurant_id,
            "branches_name": data.name,
        },
    )

    try:
        branch = await service.create_branch(
            restaurant_id=restaurant_id,
            branch_data=data,
        )
        return branch

    except BranchLimitExceededError as e:
        logger.warning(
            "api_create_branch_limit_exceeded",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_create_branch_conflict",
            extra={
                "restaurant_id": restaurant_id,
                "branches_name": data.name,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_branch_validation_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_branch_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء الفرع",
        )


# ==============================================
# UPDATE BRANCH
# ==============================================


@router.patch(
    "/{branch_id}",
    response_model=BranchResponse,
    summary="تحديث فرع",
    description="تحديث فرع موجود",
)
async def update_branch(
    *,
    branch_id: int = Path(..., ge=1, description="معرف الفرع"),
    data: BranchUpdate,
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """
    تحديث فرع موجود.

    Args:
        branch_id: معرف الفرع
        data: بيانات التحديث
        service: خدمة الفروع

    Returns:
        BranchResponse: الفرع المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على الفرع أو حدث تعارض
    """
    logger.info(
        "api_update_branch",
        extra={
            "branch_id": branch_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        branch = await service.update_branch(
            branch_id=branch_id,
            update_data=data,
        )
        return branch

    except NotFoundError as e:
        logger.warning(
            "api_branch_not_found_for_update",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_update_branch_conflict",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_branch_validation_error",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_branch_error",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث الفرع",
        )


# ==============================================
# UPDATE BRANCH STATUS
# ==============================================


@router.patch(
    "/{branch_id}/status",
    response_model=BranchResponse,
    summary="تحديث حالة الفرع",
    description="تفعيل أو إلغاء تفعيل فرع",
)
async def update_branch_status(
    *,
    branch_id: int = Path(..., ge=1, description="معرف الفرع"),
    data: BranchStatusUpdate,
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """
    تحديث حالة الفرع.

    Args:
        branch_id: معرف الفرع
        data: بيانات تحديث الحالة
        service: خدمة الفروع

    Returns:
        BranchResponse: الفرع المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على الفرع
    """
    logger.info(
        "api_update_branch_status",
        extra={
            "branch_id": branch_id,
            "is_active": data.is_active,
        },
    )

    try:
        branch = await service.update_branch_status(
            branch_id=branch_id,
            status_data=data,
        )
        return branch

    except NotFoundError as e:
        logger.warning(
            "api_branch_not_found_for_status",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_branch_status_error",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث حالة الفرع",
        )


# ==============================================
# ACTIVATE BRANCH
# ==============================================


@router.post(
    "/{branch_id}/activate",
    response_model=BranchResponse,
    summary="تفعيل فرع",
    description="تفعيل فرع (تعيين is_active = true)",
)
async def activate_branch(
    *,
    branch_id: int = Path(..., ge=1, description="معرف الفرع"),
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """
    تفعيل فرع.

    Args:
        branch_id: معرف الفرع
        service: خدمة الفروع

    Returns:
        BranchResponse: الفرع المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على الفرع
    """
    logger.info(
        "api_activate_branch",
        extra={"branch_id": branch_id},
    )

    try:
        branch = await service.activate_branch(branch_id=branch_id)
        return branch

    except NotFoundError as e:
        logger.warning(
            "api_branch_not_found_for_activate",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_activate_branch_error",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تفعيل الفرع",
        )


# ==============================================
# DEACTIVATE BRANCH
# ==============================================


@router.post(
    "/{branch_id}/deactivate",
    response_model=BranchResponse,
    summary="إلغاء تفعيل فرع",
    description="إلغاء تفعيل فرع (تعيين is_active = false)",
)
async def deactivate_branch(
    *,
    branch_id: int = Path(..., ge=1, description="معرف الفرع"),
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """
    إلغاء تفعيل فرع.

    Args:
        branch_id: معرف الفرع
        service: خدمة الفروع

    Returns:
        BranchResponse: الفرع المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على الفرع
    """
    logger.info(
        "api_deactivate_branch",
        extra={"branch_id": branch_id},
    )

    try:
        branch = await service.deactivate_branch(branch_id=branch_id)
        return branch

    except NotFoundError as e:
        logger.warning(
            "api_branch_not_found_for_deactivate",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_deactivate_branch_error",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إلغاء تفعيل الفرع",
        )


# ==============================================
# DELETE BRANCH
# ==============================================


@router.delete(
    "/{branch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف فرع",
    description="حذف فرع موجود",
)
async def delete_branch(
    *,
    branch_id: int = Path(..., ge=1, description="معرف الفرع"),
    permanent: bool = Query(
        False,
        description="حذف نهائي (بدلاً من الحذف المنطقي)",
    ),
    service: BranchService = Depends(get_branch_service),
) -> None:
    """
    حذف فرع.

    Args:
        branch_id: معرف الفرع
        permanent: حذف نهائي
        service: خدمة الفروع

    Raises:
        HTTPException: إذا لم يتم العثور على الفرع
    """
    logger.info(
        "api_delete_branch",
        extra={
            "branch_id": branch_id,
            "permanent": permanent,
        },
    )

    try:
        await service.delete_branch(
            branch_id=branch_id,
            permanent=permanent,
        )

    except NotFoundError as e:
        logger.warning(
            "api_branch_not_found_for_delete",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_delete_branch_validation_error",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_branch_error",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف الفرع",
        )

    logger.info(
        "api_branch_deleted_successfully",
        extra={
            "branch_id": branch_id,
            "permanent": permanent,
        },
    )


# ==============================================
# GET BRANCH SUMMARY
# ==============================================


@router.get(
    "/stats/summary",
    response_model=BranchSummary,
    summary="ملخص الفروع",
    description="الحصول على ملخص الفروع لمطعم معين",
)
async def get_branch_summary(
    *,
    restaurant_id: int = Query(
        ...,
        description="معرف المطعم",
        ge=1,
    ),
    service: BranchService = Depends(get_branch_service),
) -> BranchSummary:
    """
    الحصول على ملخص الفروع.

    Args:
        restaurant_id: معرف المطعم
        service: خدمة الفروع

    Returns:
        BranchSummary: ملخص الفروع

    Raises:
        HTTPException: إذا حدث خطأ
    """
    logger.info(
        "api_get_branch_summary",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        summary = await service.get_branch_summary(
            restaurant_id=restaurant_id,
        )
        return summary

    except NotFoundError as e:
        logger.warning(
            "api_branch_summary_not_found",
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
            "api_get_branch_summary_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب ملخص الفروع",
        )


# ==============================================
# GET RESTAURANT BRANCHES
# ==============================================


@router.get(
    "/restaurant/{restaurant_id}",
    response_model=BranchListResponse,
    summary="فروع المطعم",
    description="الحصول على فروع مطعم معين",
)
async def get_restaurant_branches(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    only_active: bool = Query(
        True,
        description="جلب الفروع النشطة فقط",
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
    service: BranchService = Depends(get_branch_service),
) -> BranchListResponse:
    """
    الحصول على فروع مطعم معين.

    Args:
        restaurant_id: معرف المطعم
        only_active: جلب الفروع النشطة فقط
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة الفروع

    Returns:
        BranchListResponse: قائمة الفروع مع الإحصائيات
    """
    logger.info(
        "api_get_restaurant_branches",
        extra={
            "restaurant_id": restaurant_id,
            "only_active": only_active,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        result = await service.get_by_restaurant(
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
            only_active=only_active,
        )
        return result

    except Exception as e:
        logger.exception(
            "api_get_restaurant_branches_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب فروع المطعم",
        )


# ==============================================
# GET BRANCH COST
# ==============================================


@router.get(
    "/{branch_id}/cost",
    summary="تكلفة الفرع",
    description="الحصول على تكلفة الفرع",
)
async def get_branch_cost(
    *,
    branch_id: int = Path(..., ge=1, description="معرف الفرع"),
    service: BranchService = Depends(get_branch_service),
) -> BranchCostResponse:
    """
    الحصول على تكلفة الفرع.

    Args:
        branch_id: معرف الفرع
        service: خدمة الفروع

    Returns:
        BranchCostResponse: تفاصيل تكلفة الفرع

    Raises:
        HTTPException: إذا لم يتم العثور على الفرع
    """
    logger.info(
        "api_get_branch_cost",
        extra={"branch_id": branch_id},
    )

    try:
        branch = await service.get_by_id(branch_id=branch_id)

        # حساب تكلفة الفروع للمطعم
        total_cost = await service.get_branch_cost(
            restaurant_id=branch.restaurant_id,
        )

        branches_count = await service.count_by_restaurant(
            restaurant_id=branch.restaurant_id,
        )

        # تكلفة الفرع الواحد (متوسط)
        avg_cost_per_branch = total_cost / branches_count if branches_count > 0 else 0

        return {
            "branch_id": branch_id,
            "restaurant_id": branch.restaurant_id,
            "branch_name": branch.name,
            "total_branches": branches_count,
            "total_cost": total_cost,
            "avg_cost_per_branch": avg_cost_per_branch,
        }

    except NotFoundError as e:
        logger.warning(
            "api_branch_not_found_for_cost",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_branch_cost_error",
            extra={
                "branch_id": branch_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حساب تكلفة الفرع",
        )
