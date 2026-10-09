# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📋 ADMIN LOG API
# واجهات API لسجل أنشطة المديرين
# ==============================================

"""MoulAI operational module for admin log.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from datetime import datetime
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

from app.core.database import get_db
from app.core.logger import logger
from app.core.exceptions import NotFoundError
from app.schemas.admin_log import (
    AdminLogCreate,
    AdminLogResponse,
    AdminLogListResponse,
    AdminLogFilter,
    ActionSummary,
    ActionsSummaryResponse,
)
from app.services.business.admin.admin_log_service import AdminLogService

# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/admin-logs",
    tags=["Admin Logs"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================


async def get_admin_log_service(
    session: AsyncSession = Depends(get_db),
) -> AdminLogService:
    """
    الحصول على خدمة سجل أنشطة المديرين.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        AdminLogService: مثيل من AdminLogService
    """
    return AdminLogService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# CREATE ADMIN LOG
# ==============================================


@router.post(
    "/",
    response_model=AdminLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء سجل نشاط",
    description="إنشاء سجل نشاط جديد للمدير",
)
async def create_admin_log(
    *,
    data: AdminLogCreate,
    service: AdminLogService = Depends(get_admin_log_service),
) -> AdminLogResponse:
    """
    إنشاء سجل نشاط جديد.

    Args:
        data: بيانات سجل النشاط

    Returns:
        AdminLogResponse: سجل النشاط المنشأ
    """
    logger.info(
        "api_create_admin_log",
        extra={
            "admin_id": data.admin_id,
            "action": data.action,
        },
    )

    try:
        log = await service.create_log(log_data=data)
        return log

    except Exception as e:
        logger.exception(
            "api_create_admin_log_error",
            extra={
                "admin_id": data.admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء سجل النشاط",
        )


# ==============================================
# GET ADMIN LOG BY ID
# ==============================================


@router.get(
    "/{log_id}",
    response_model=AdminLogResponse,
    summary="الحصول على سجل نشاط بالمعرف",
    description="الحصول على سجل نشاط محدد بواسطة معرفه",
)
async def get_admin_log_by_id(
    *,
    log_id: int = Path(..., ge=1, description="معرف سجل النشاط"),
    service: AdminLogService = Depends(get_admin_log_service),
) -> AdminLogResponse:
    """
    الحصول على سجل نشاط بالمعرف.

    Args:
        log_id: معرف سجل النشاط

    Returns:
        AdminLogResponse: سجل النشاط المطلوب

    Raises:
        HTTPException: إذا لم يتم العثور على السجل
    """
    logger.info(
        "api_get_admin_log_by_id",
        extra={"log_id": log_id},
    )

    try:
        log = await service.get_log_by_id(log_id=log_id)
        return log

    except NotFoundError as e:
        logger.warning(
            "api_admin_log_not_found",
            extra={
                "log_id": log_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_admin_log_by_id_error",
            extra={
                "log_id": log_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب سجل النشاط",
        )


# ==============================================
# GET ADMIN LOGS BY ADMIN
# ==============================================


@router.get(
    "/admin/{admin_id}",
    response_model=AdminLogListResponse,
    summary="سجل أنشطة مدير معين",
    description="الحصول على سجل أنشطة مدير محدد",
)
async def get_admin_logs_by_admin(
    *,
    admin_id: int = Path(..., ge=1, description="معرف المدير"),
    action: Optional[str] = Query(None, description="تصفية حسب نوع الإجراء"),
    resource: Optional[str] = Query(None, description="تصفية حسب نوع المورد"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: AdminLogService = Depends(get_admin_log_service),
) -> AdminLogListResponse:
    """
    الحصول على سجل أنشطة مدير معين.

    Args:
        admin_id: معرف المدير
        action: تصفية حسب نوع الإجراء
        resource: تصفية حسب نوع المورد
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        AdminLogListResponse: قائمة سجل الأنشطة
    """
    logger.info(
        "api_get_admin_logs_by_admin",
        extra={
            "admin_id": admin_id,
            "action": action,
            "resource": resource,
        },
    )

    try:
        filters = AdminLogFilter(
            action=action,
            resource=resource,
        )
        return await service.get_logs_by_admin(
            admin_id=admin_id,
            filters=filters,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_get_admin_logs_by_admin_error",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب سجل أنشطة المدير",
        )


# ==============================================
# SEARCH ADMIN LOGS
# ==============================================


@router.get(
    "/search",
    response_model=AdminLogListResponse,
    summary="البحث في سجل الأنشطة",
    description="البحث في سجل الأنشطة حسب النص",
)
async def search_admin_logs(
    *,
    query: str = Query(..., min_length=1, max_length=255, description="نص البحث"),
    admin_id: Optional[int] = Query(None, description="معرف المدير"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: AdminLogService = Depends(get_admin_log_service),
) -> AdminLogListResponse:
    """
    البحث في سجل الأنشطة.

    Args:
        query: نص البحث
        admin_id: معرف المدير (اختياري)
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        AdminLogListResponse: قائمة سجل الأنشطة المطابقة
    """
    logger.info(
        "api_search_admin_logs",
        extra={
            "query": query,
            "admin_id": admin_id,
        },
    )

    try:
        return await service.search_logs(
            query=query,
            admin_id=admin_id,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_search_admin_logs_error",
            extra={
                "query": query,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء البحث في سجل الأنشطة",
        )


# ==============================================
# GET ACTIONS SUMMARY
# ==============================================


@router.get(
    "/summary/actions",
    response_model=ActionsSummaryResponse,
    summary="ملخص الإجراءات",
    description="الحصول على ملخص الإجراءات حسب النوع",
)
async def get_actions_summary(
    *,
    admin_id: Optional[int] = Query(None, description="معرف المدير"),
    limit: int = Query(10, ge=1, le=50, description="الحد الأقصى للنتائج"),
    service: AdminLogService = Depends(get_admin_log_service),
) -> ActionsSummaryResponse:
    """
    الحصول على ملخص الإجراءات حسب النوع.

    Args:
        admin_id: معرف المدير (اختياري)
        limit: الحد الأقصى للنتائج

    Returns:
        ActionsSummaryResponse: ملخص الإجراءات
    """
    logger.info(
        "api_get_actions_summary",
        extra={
            "admin_id": admin_id,
            "limit": limit,
        },
    )

    try:
        summary = await service.get_actions_summary(
            admin_id=admin_id,
            limit=limit,
        )
        total = len(summary)

        return ActionsSummaryResponse(
            items=[
                ActionSummary(action=item["action"], count=item["count"])
                for item in summary
            ],
            total=total,
        )

    except Exception as e:
        logger.exception(
            "api_get_actions_summary_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب ملخص الإجراءات",
        )


# ==============================================
# GET RECENT ACTIVITY
# ==============================================


@router.get(
    "/recent",
    response_model=List[AdminLogResponse],
    summary="أحدث الأنشطة",
    description="الحصول على أحدث الأنشطة",
)
async def get_recent_activity(
    *,
    admin_id: Optional[int] = Query(None, description="معرف المدير"),
    limit: int = Query(10, ge=1, le=50, description="عدد النتائج"),
    service: AdminLogService = Depends(get_admin_log_service),
) -> List[AdminLogResponse]:
    """
    الحصول على أحدث الأنشطة.

    Args:
        admin_id: معرف المدير (اختياري)
        limit: عدد النتائج

    Returns:
        List[AdminLogResponse]: قائمة أحدث الأنشطة
    """
    logger.info(
        "api_get_recent_activity",
        extra={
            "admin_id": admin_id,
            "limit": limit,
        },
    )

    try:
        return await service.get_recent_activity(
            admin_id=admin_id,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_get_recent_activity_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب أحدث الأنشطة",
        )


# ==============================================
# GET LOGS BY DATE RANGE
# ==============================================


@router.get(
    "/date-range",
    response_model=AdminLogListResponse,
    summary="سجل الأنشطة حسب النطاق الزمني",
    description="الحصول على سجل الأنشطة في نطاق زمني محدد",
)
async def get_logs_by_date_range(
    *,
    start_date: datetime = Query(..., description="تاريخ البداية"),
    end_date: datetime = Query(..., description="تاريخ النهاية"),
    admin_id: Optional[int] = Query(None, description="معرف المدير"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: AdminLogService = Depends(get_admin_log_service),
) -> AdminLogListResponse:
    """
    الحصول على سجل الأنشطة في نطاق زمني محدد.

    Args:
        start_date: تاريخ البداية
        end_date: تاريخ النهاية
        admin_id: معرف المدير (اختياري)
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        AdminLogListResponse: قائمة سجل الأنشطة
    """
    logger.info(
        "api_get_logs_by_date_range",
        extra={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "admin_id": admin_id,
        },
    )

    try:
        return await service.get_logs_by_date_range(
            start_date=start_date,
            end_date=end_date,
            admin_id=admin_id,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_get_logs_by_date_range_error",
            extra={
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب سجل الأنشطة حسب النطاق الزمني",
        )


# ==============================================
# GET LOGS BY ACTION
# ==============================================


@router.get(
    "/action/{action}",
    response_model=AdminLogListResponse,
    summary="سجل الأنشطة حسب الإجراء",
    description="الحصول على سجل الأنشطة حسب نوع الإجراء",
)
async def get_logs_by_action(
    *,
    action: str = Path(..., min_length=1, max_length=50, description="نوع الإجراء"),
    admin_id: Optional[int] = Query(None, description="معرف المدير"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: AdminLogService = Depends(get_admin_log_service),
) -> AdminLogListResponse:
    """
    الحصول على سجل الأنشطة حسب نوع الإجراء.

    Args:
        action: نوع الإجراء
        admin_id: معرف المدير (اختياري)
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        AdminLogListResponse: قائمة سجل الأنشطة
    """
    logger.info(
        "api_get_logs_by_action",
        extra={
            "action": action,
            "admin_id": admin_id,
        },
    )

    try:
        return await service.get_logs_by_action(
            action=action,
            admin_id=admin_id,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_get_logs_by_action_error",
            extra={
                "action": action,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب سجل الأنشطة حسب الإجراء",
        )
