# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔐 ADMIN SESSION API
# واجهات API لجلسات المديرين
# ==============================================

"""Administrative session operations require trusted Keycloak identity and RBAC.

Legacy session tokens and admin identifiers cannot replace API authentication.
Session credentials are accepted only in headers or JSON bodies, never URLs.
"""

from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Path,
    Query,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin_permission
from app.core.database import get_db
from app.core.exceptions import (
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.core.logger import logger
from app.schemas.admin_session import (
    AdminSessionCreate,
    AdminSessionExtend,
    AdminSessionListResponse,
    AdminSessionResponse,
    AdminSessionStatistics,
)
from app.services.business.admin.admin_session_service import AdminSessionService

# ==============================================
# 🏗️ ROUTER
# ==============================================


async def reject_session_credentials_in_url(*, request: Request) -> None:
    """Reject retired credential query inputs before administrative business IO."""
    if {"session_token", "except_session_token"}.intersection(request.query_params):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Session credentials must be sent in the documented headers.",
        )


router = APIRouter(
    prefix="/admin-sessions",
    tags=["Admin Sessions"],
    dependencies=[
        Depends(require_admin_permission("admins.manage")),
        Depends(reject_session_credentials_in_url),
    ],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================


async def get_admin_session_service(
    *,
    session: AsyncSession = Depends(get_db),
) -> AdminSessionService:
    """
    الحصول على خدمة جلسات المديرين.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        AdminSessionService: مثيل من AdminSessionService
    """
    return AdminSessionService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# CREATE SESSION
# ==============================================


@router.post(
    "/",
    response_model=AdminSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء جلسة مدير",
    description="إنشاء جلسة جديدة للمدير",
)
async def create_admin_session(
    *,
    data: AdminSessionCreate,
    service: AdminSessionService = Depends(get_admin_session_service),
) -> AdminSessionResponse:
    """
    إنشاء جلسة جديدة للمدير.

    Args:
        data: بيانات الجلسة

    Returns:
        AdminSessionResponse: الجلسة المنشأة

    Raises:
        HTTPException: إذا لم يتم العثور على المدير
    """
    logger.info(
        "api_create_admin_session",
        extra={
            "admin_id": data.admin_id,
            "expires_at": data.expires_at,
        },
    )

    try:
        session = await service.create_session(session_data=data)
        return session

    except NotFoundError as e:
        logger.warning(
            "api_admin_not_found_for_session",
            extra={
                "admin_id": data.admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_admin_session_validation_error",
            extra={
                "admin_id": data.admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "api_create_admin_session_error",
            extra={
                "admin_id": data.admin_id,
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء جلسة المدير",
        )


# ==============================================
# GET SESSION BY TOKEN
# ==============================================


@router.get(
    "/lookup",
    response_model=AdminSessionResponse,
    summary="الحصول على جلسة بالرمز",
    description="الحصول على جلسة مدير بواسطة رمز الجلسة",
)
async def get_session_by_token(
    *,
    session_token: str = Header(
        ...,
        alias="X-Admin-Session-Token",
        min_length=1,
        max_length=255,
        pattern=r"\S",
        description="Session credential; does not replace trusted OIDC authentication.",
    ),
    service: AdminSessionService = Depends(get_admin_session_service),
) -> AdminSessionResponse:
    """
    الحصول على جلسة بواسطة رمز الجلسة.

    Args:
        session_token: رمز الجلسة

    Returns:
        AdminSessionResponse: الجلسة المطلوبة

    Raises:
        HTTPException: إذا لم يتم العثور على الجلسة
    """
    logger.info(
        "api_get_session_by_token",
    )

    try:
        session = await service.get_session_by_token(
            session_token=session_token.strip()
        )
        return session

    except NotFoundError as e:
        logger.warning(
            "api_admin_session_not_found",
            extra={
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "api_get_session_by_token_error",
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب الجلسة",
        )


# ==============================================
# GET ACTIVE SESSION
# ==============================================


@router.get(
    "/lookup/active",
    response_model=AdminSessionResponse,
    summary="الحصول على جلسة نشطة",
    description="الحصول على جلسة مدير نشطة بواسطة رمز الجلسة",
)
async def get_active_session(
    *,
    session_token: str = Header(
        ...,
        alias="X-Admin-Session-Token",
        min_length=1,
        max_length=255,
        pattern=r"\S",
        description="Session credential; does not replace trusted OIDC authentication.",
    ),
    service: AdminSessionService = Depends(get_admin_session_service),
) -> AdminSessionResponse:
    """
    الحصول على جلسة نشطة بواسطة رمز الجلسة.

    Args:
        session_token: رمز الجلسة

    Returns:
        AdminSessionResponse: الجلسة النشطة

    Raises:
        HTTPException: إذا لم يتم العثور على الجلسة أو كانت منتهية
    """
    logger.info(
        "api_get_active_session",
    )

    try:
        session = await service.get_active_session(session_token=session_token.strip())
        return session

    except NotFoundError as e:
        logger.warning(
            "api_admin_session_not_found_active",
            extra={
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except UnauthorizedError as e:
        logger.warning(
            "api_admin_session_unauthorized",
            extra={
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "api_get_active_session_error",
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب الجلسة النشطة",
        )


# ==============================================
# GET SESSION STATUS
# ==============================================


@router.get(
    "/lookup/status",
    summary="حالة الجلسة",
    description="الحصول على حالة جلسة المدير",
)
async def get_session_status(
    *,
    session_token: str = Header(
        ...,
        alias="X-Admin-Session-Token",
        min_length=1,
        max_length=255,
        pattern=r"\S",
        description="Session credential; does not replace trusted OIDC authentication.",
    ),
    service: AdminSessionService = Depends(get_admin_session_service),
) -> dict[str, bool | int | str | None]:
    """
    الحصول على حالة الجلسة.

    Args:
        session_token: رمز الجلسة

    Returns:
        dict: حالة الجلسة

    Raises:
        HTTPException: إذا لم يتم العثور على الجلسة
    """
    logger.info(
        "api_get_session_status",
    )

    try:
        return await service.get_session_status(session_token=session_token.strip())

    except NotFoundError as e:
        logger.warning(
            "api_session_not_found_for_status",
            extra={
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "api_get_session_status_error",
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب حالة الجلسة",
        )


# ==============================================
# GET SESSIONS BY ADMIN
# ==============================================


@router.get(
    "/admin/{admin_id:int}",
    response_model=AdminSessionListResponse,
    summary="جلسات المدير",
    description="الحصول على جلسات مدير معين",
)
async def get_sessions_by_admin(
    *,
    admin_id: int = Path(..., ge=1, description="معرف المدير"),
    only_active: bool = Query(True, description="جلب الجلسات النشطة فقط"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: AdminSessionService = Depends(get_admin_session_service),
) -> AdminSessionListResponse:
    """
    الحصول على جلسات مدير معين.

    Args:
        admin_id: معرف المدير
        only_active: جلب الجلسات النشطة فقط
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        AdminSessionListResponse: قائمة جلسات المدير
    """
    logger.info(
        "api_get_sessions_by_admin",
        extra={
            "admin_id": admin_id,
            "only_active": only_active,
        },
    )

    try:
        return await service.get_sessions_by_admin(
            admin_id=admin_id,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error(
            "api_get_sessions_by_admin_error",
            extra={
                "admin_id": admin_id,
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب جلسات المدير",
        )


# ==============================================
# GET ACTIVE SESSIONS BY ADMIN
# ==============================================


@router.get(
    "/admin/{admin_id:int}/active",
    response_model=AdminSessionListResponse,
    summary="الجلسات النشطة للمدير",
    description="الحصول على الجلسات النشطة لمدير معين",
)
async def get_active_sessions_by_admin(
    *,
    admin_id: int = Path(..., ge=1, description="معرف المدير"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: AdminSessionService = Depends(get_admin_session_service),
) -> AdminSessionListResponse:
    """
    الحصول على الجلسات النشطة لمدير معين.

    Args:
        admin_id: معرف المدير
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        AdminSessionListResponse: قائمة الجلسات النشطة
    """
    logger.info(
        "api_get_active_sessions_by_admin",
        extra={
            "admin_id": admin_id,
        },
    )

    try:
        return await service.get_active_sessions_by_admin(
            admin_id=admin_id,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error(
            "api_get_active_sessions_by_admin_error",
            extra={
                "admin_id": admin_id,
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب الجلسات النشطة للمدير",
        )


# ==============================================
# UPDATE ACTIVITY
# ==============================================


@router.patch(
    "/lookup/activity",
    response_model=AdminSessionResponse,
    summary="تحديث آخر نشاط",
    description="تحديث آخر نشاط لجلسة المدير",
)
async def update_activity(
    *,
    session_token: str = Header(
        ...,
        alias="X-Admin-Session-Token",
        min_length=1,
        max_length=255,
        pattern=r"\S",
        description="Session credential; does not replace trusted OIDC authentication.",
    ),
    service: AdminSessionService = Depends(get_admin_session_service),
) -> AdminSessionResponse:
    """
    تحديث آخر نشاط للجلسة.

    Args:
        session_token: رمز الجلسة

    Returns:
        AdminSessionResponse: الجلسة المحدثة

    Raises:
        HTTPException: إذا لم يتم العثور على الجلسة
    """
    logger.info(
        "api_update_activity",
    )

    try:
        session = await service.update_activity(session_token=session_token.strip())
        return session

    except NotFoundError as e:
        logger.warning(
            "api_session_not_found_for_activity",
            extra={
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "api_update_activity_error",
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث آخر نشاط للجلسة",
        )


# ==============================================
# DEACTIVATE SESSION
# ==============================================


@router.delete(
    "/lookup/deactivate",
    response_model=AdminSessionResponse,
    summary="إلغاء تنشيط جلسة",
    description="إلغاء تنشيط جلسة مدير (تسجيل الخروج)",
)
async def deactivate_session(
    *,
    session_token: str = Header(
        ...,
        alias="X-Admin-Session-Token",
        min_length=1,
        max_length=255,
        pattern=r"\S",
        description="Session credential; does not replace trusted OIDC authentication.",
    ),
    service: AdminSessionService = Depends(get_admin_session_service),
) -> AdminSessionResponse:
    """
    إلغاء تنشيط جلسة مدير (تسجيل الخروج).

    Args:
        session_token: رمز الجلسة

    Returns:
        AdminSessionResponse: الجلسة المحدثة

    Raises:
        HTTPException: إذا لم يتم العثور على الجلسة
    """
    logger.info(
        "api_deactivate_session",
    )

    try:
        session = await service.deactivate_session(session_token=session_token.strip())
        return session

    except NotFoundError as e:
        logger.warning(
            "api_admin_session_not_found_for_deactivate",
            extra={
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "api_deactivate_session_error",
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إلغاء تنشيط الجلسة",
        )


# ==============================================
# DEACTIVATE ALL SESSIONS
# ==============================================


@router.delete(
    "/admin/{admin_id:int}/all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="إلغاء تنشيط جميع جلسات المدير",
    description="إلغاء تنشيط جميع جلسات مدير معين",
)
async def deactivate_all_sessions(
    *,
    admin_id: int = Path(..., ge=1, description="معرف المدير"),
    except_session_token: Optional[str] = Header(
        None,
        alias="X-Preserve-Session-Token",
        min_length=1,
        max_length=255,
        pattern=r"\S",
        description="Optional session credential to preserve; never put it in a URL.",
    ),
    service: AdminSessionService = Depends(get_admin_session_service),
) -> None:
    """
    إلغاء تنشيط جميع جلسات مدير معين.

    Args:
        admin_id: معرف المدير
        except_session_token: استثناء جلسة معينة

    Raises:
        HTTPException: إذا حدث خطأ
    """
    logger.info(
        "api_deactivate_all_sessions",
        extra={
            "admin_id": admin_id,
        },
    )

    try:
        await service.deactivate_all_sessions(
            admin_id=admin_id,
            except_session_token=(
                except_session_token.strip()
                if except_session_token is not None
                else None
            ),
        )

    except Exception as e:
        logger.error(
            "api_deactivate_all_sessions_error",
            extra={
                "admin_id": admin_id,
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إلغاء تنشيط جميع جلسات المدير",
        )

    logger.info(
        "api_all_admin_sessions_deactivated",
        extra={"admin_id": admin_id},
    )


# ==============================================
# EXTEND SESSION
# ==============================================


@router.patch(
    "/extend",
    response_model=AdminSessionResponse,
    summary="تمديد صلاحية الجلسة",
    description="تمديد صلاحية جلسة المدير",
)
async def extend_session(
    *,
    data: AdminSessionExtend,
    service: AdminSessionService = Depends(get_admin_session_service),
) -> AdminSessionResponse:
    """
    تمديد صلاحية الجلسة.

    Args:
        data: بيانات تمديد الجلسة

    Returns:
        AdminSessionResponse: الجلسة المحدثة

    Raises:
        HTTPException: إذا لم يتم العثور على الجلسة أو كان التاريخ غير صحيح
    """
    logger.info(
        "api_extend_session",
        extra={
            "expires_at": data.expires_at,
        },
    )

    try:
        session = await service.extend_session(extend_data=data)
        return session

    except NotFoundError as e:
        logger.warning(
            "api_admin_session_not_found_for_extend",
            extra={
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_extend_session_validation_error",
            extra={
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "api_extend_session_error",
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تمديد صلاحية الجلسة",
        )


# ==============================================
# GET SESSION STATISTICS
# ==============================================


@router.get(
    "/statistics",
    response_model=AdminSessionStatistics,
    summary="إحصائيات الجلسات",
    description="الحصول على إحصائيات جلسات المديرين",
)
async def get_session_statistics(
    *,
    admin_id: Optional[int] = Query(None, description="معرف المدير"),
    service: AdminSessionService = Depends(get_admin_session_service),
) -> AdminSessionStatistics:
    """
    الحصول على إحصائيات جلسات المديرين.

    Args:
        admin_id: معرف المدير (اختياري)

    Returns:
        AdminSessionStatistics: إحصائيات الجلسات
    """
    logger.info(
        "api_get_session_statistics",
        extra={"admin_id": admin_id},
    )

    try:
        stats = await service.get_statistics(admin_id=admin_id)
        return AdminSessionStatistics(
            total_sessions=stats["total_sessions"],
            active_sessions=stats["active_sessions"],
            expired_sessions=stats["expired_sessions"],
            admin_id=admin_id,
        )

    except Exception as e:
        logger.error(
            "api_get_session_statistics_error",
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب إحصائيات الجلسات",
        )


# ==============================================
# CLEANUP EXPIRED SESSIONS
# ==============================================


@router.post(
    "/cleanup",
    summary="تنظيف الجلسات المنتهية",
    description="تنظيف الجلسات المنتهية من النظام",
)
async def cleanup_expired_sessions(
    *,
    days: int = Query(
        30, ge=1, le=365, description="عدد الأيام للاحتفاظ بالجلسات المنتهية"
    ),
    service: AdminSessionService = Depends(get_admin_session_service),
) -> dict:
    """
    تنظيف الجلسات المنتهية.

    Args:
        days: عدد الأيام للاحتفاظ بالجلسات المنتهية

    Returns:
        dict: عدد الجلسات المنظفة
    """
    logger.info(
        "api_cleanup_expired_sessions",
        extra={"days": days},
    )

    try:
        count = await service.cleanup_expired_sessions(days=days)

        return {
            "status": "success",
            "cleaned_count": count,
            "message": f"تم تنظيف {count} جلسة منتهية",
        }

    except Exception as e:
        logger.error(
            "api_cleanup_expired_sessions_error",
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تنظيف الجلسات المنتهية",
        )
