# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 👑 ADMINS API
# نقاط نهاية API للمديرين (CRUD)
# تدير عمليات إنشاء واستعراض وتحديث وحذف المديرين
# ==============================================

"""MoulAI operational module for admin.

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

from app.core.database import get_db
from app.core.logger import logger
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.schemas.admin import (
    AdminCreate,
    AdminResponse,
    AdminUpdate,
    AdminListResponse,
    AdminStatistics,
)
from app.services.business.admin.admin_service import AdminService

# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/admins",
    tags=["Admins"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================


async def get_admin_service(
    session: AsyncSession = Depends(get_db),
) -> AdminService:
    """
    الحصول على خدمة المديرين.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        AdminService: مثيل من AdminService
    """
    return AdminService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# CREATE ADMIN
# ==============================================


@router.post(
    "/",
    response_model=AdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء مدير جديد",
    description="إنشاء مدير جديد في النظام",
)
async def create_admin(
    *,
    data: AdminCreate,
    service: AdminService = Depends(get_admin_service),
) -> AdminResponse:
    """
    إنشاء مدير جديد.

    Args:
        data: بيانات المدير

    Returns:
        AdminResponse: المدير المنشأ

    Raises:
        HTTPException: إذا كان اسم المستخدم أو chat_id موجوداً مسبقاً
    """
    logger.info(
        "api_create_admin",
        extra={
            "username": data.username,
            "chat_id": data.chat_id,
        },
    )

    try:
        admin = await service.create_admin(admin_data=data)
        return admin

    except ConflictError as e:
        logger.warning(
            "api_create_admin_conflict",
            extra={
                "username": data.username,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_admin_validation_error",
            extra={
                "username": data.username,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_admin_error",
            extra={
                "username": data.username,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء المدير",
        )


# ==============================================
# GET ADMIN BY ID
# ==============================================


@router.get(
    "/{admin_id}",
    response_model=AdminResponse,
    summary="الحصول على مدير بالمعرف",
    description="الحصول على مدير محدد بواسطة معرفه",
)
async def get_admin_by_id(
    *,
    admin_id: int = Path(..., ge=1, description="معرف المدير"),
    include_inactive: bool = Query(False, description="تضمين المديرين غير النشطين"),
    service: AdminService = Depends(get_admin_service),
) -> AdminResponse:
    """
    الحصول على مدير بالمعرف.

    Args:
        admin_id: معرف المدير
        include_inactive: تضمين المديرين غير النشطين

    Returns:
        AdminResponse: المدير المطلوب

    Raises:
        HTTPException: إذا لم يتم العثور على المدير
    """
    logger.info(
        "api_get_admin_by_id",
        extra={
            "admin_id": admin_id,
            "include_inactive": include_inactive,
        },
    )

    try:
        admin = await service.get_admin_by_id(
            admin_id=admin_id,
            include_inactive=include_inactive,
        )
        return admin

    except NotFoundError as e:
        logger.warning(
            "api_admin_not_found",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_admin_by_id_error",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب المدير",
        )


# ==============================================
# GET ADMIN BY USERNAME
# ==============================================


@router.get(
    "/username/{username}",
    response_model=AdminResponse,
    summary="الحصول على مدير بواسطة اسم المستخدم",
    description="الحصول على مدير محدد بواسطة اسم المستخدم",
)
async def get_admin_by_username(
    *,
    username: str = Path(..., min_length=3, max_length=50, description="اسم المستخدم"),
    include_inactive: bool = Query(False, description="تضمين المديرين غير النشطين"),
    service: AdminService = Depends(get_admin_service),
) -> AdminResponse:
    """
    الحصول على مدير بواسطة اسم المستخدم.

    Args:
        username: اسم المستخدم
        include_inactive: تضمين المديرين غير النشطين

    Returns:
        AdminResponse: المدير المطلوب

    Raises:
        HTTPException: إذا لم يتم العثور على المدير
    """
    logger.info(
        "api_get_admin_by_username",
        extra={
            "username": username,
            "include_inactive": include_inactive,
        },
    )

    try:
        admin = await service.get_admin_by_username(
            username=username,
            include_inactive=include_inactive,
        )
        return admin

    except NotFoundError as e:
        logger.warning(
            "api_admin_not_found_by_username",
            extra={
                "username": username,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_admin_by_username_error",
            extra={
                "username": username,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب المدير",
        )


# ==============================================
# GET ADMIN BY CHAT ID
# ==============================================


@router.get(
    "/chat/{chat_id}",
    response_model=AdminResponse,
    summary="الحصول على مدير بواسطة معرف الدردشة",
    description="الحصول على مدير محدد بواسطة معرف الدردشة في Telegram",
)
async def get_admin_by_chat_id(
    *,
    chat_id: int = Path(..., ge=1, description="معرف الدردشة في Telegram"),
    include_inactive: bool = Query(False, description="تضمين المديرين غير النشطين"),
    service: AdminService = Depends(get_admin_service),
) -> AdminResponse:
    """
    الحصول على مدير بواسطة معرف الدردشة.

    Args:
        chat_id: معرف الدردشة في Telegram
        include_inactive: تضمين المديرين غير النشطين

    Returns:
        AdminResponse: المدير المطلوب

    Raises:
        HTTPException: إذا لم يتم العثور على المدير
    """
    logger.info(
        "api_get_admin_by_chat_id",
        extra={
            "chat_id": chat_id,
            "include_inactive": include_inactive,
        },
    )

    try:
        admin = await service.get_admin_by_chat_id(
            chat_id=chat_id,
            include_inactive=include_inactive,
        )
        return admin

    except NotFoundError as e:
        logger.warning(
            "api_admin_not_found_by_chat_id",
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
            "api_get_admin_by_chat_id_error",
            extra={
                "chat_id": chat_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب المدير",
        )


# ==============================================
# LIST ADMINS
# ==============================================


@router.get(
    "/",
    response_model=AdminListResponse,
    summary="قائمة المديرين",
    description="الحصول على قائمة المديرين مع إمكانية التصفية والبحث",
)
async def list_admins(
    *,
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    only_active: bool = Query(True, description="جلب المديرين النشطين فقط"),
    role: Optional[str] = Query(None, description="تصفية حسب الدور"),
    search: Optional[str] = Query(
        None, min_length=1, max_length=255, description="نص البحث"
    ),
    order_by: Optional[str] = Query("id", description="حقل الترتيب"),
    order_desc: bool = Query(False, description="ترتيب تنازلي"),
    service: AdminService = Depends(get_admin_service),
) -> AdminListResponse:
    """
    الحصول على قائمة المديرين.

    Args:
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        only_active: جلب المديرين النشطين فقط
        role: تصفية حسب الدور
        search: نص البحث
        order_by: حقل الترتيب
        order_desc: ترتيب تنازلي

    Returns:
        AdminListResponse: قائمة المديرين مع الإحصائيات
    """
    logger.info(
        "api_list_admins",
        extra={
            "skip": skip,
            "limit": limit,
            "only_active": only_active,
            "role": role,
            "search": search,
        },
    )

    try:
        if search:
            return await service.search_admins(
                query=search,
                only_active=only_active,
                skip=skip,
                limit=limit,
            )
        elif role:
            return await service.get_admins_by_role(
                role=role,
                only_active=only_active,
                skip=skip,
                limit=limit,
            )
        else:
            return await service.get_all_admins(
                only_active=only_active,
                skip=skip,
                limit=limit,
                order_by=order_by,
                order_desc=order_desc,
            )

    except Exception as e:
        logger.exception(
            "api_list_admins_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة المديرين",
        )


# ==============================================
# UPDATE ADMIN
# ==============================================


@router.patch(
    "/{admin_id}",
    response_model=AdminResponse,
    summary="تحديث مدير",
    description="تحديث بيانات مدير موجود",
)
async def update_admin(
    *,
    admin_id: int = Path(..., ge=1, description="معرف المدير"),
    data: AdminUpdate,
    service: AdminService = Depends(get_admin_service),
) -> AdminResponse:
    """
    تحديث مدير موجود.

    Args:
        admin_id: معرف المدير
        data: بيانات التحديث

    Returns:
        AdminResponse: المدير المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على المدير أو حدث تعارض
    """
    logger.info(
        "api_update_admin",
        extra={
            "admin_id": admin_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        admin = await service.update_admin(
            admin_id=admin_id,
            update_data=data,
        )
        return admin

    except NotFoundError as e:
        logger.warning(
            "api_admin_not_found_for_update",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_update_admin_conflict",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_admin_validation_error",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_admin_error",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث المدير",
        )


# ==============================================
# UPDATE ADMIN ROLE
# ==============================================


@router.patch(
    "/{admin_id}/role",
    response_model=AdminResponse,
    summary="تحديث دور المدير",
    description="تحديث دور مدير موجود",
)
async def update_admin_role(
    *,
    admin_id: int = Path(..., ge=1, description="معرف المدير"),
    role: str = Query(..., description="الدور الجديد (super_admin, admin, manager)"),
    service: AdminService = Depends(get_admin_service),
) -> AdminResponse:
    """
    تحديث دور المدير.

    Args:
        admin_id: معرف المدير
        role: الدور الجديد

    Returns:
        AdminResponse: المدير المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على المدير
    """
    logger.info(
        "api_update_admin_role",
        extra={
            "admin_id": admin_id,
            "role": role,
        },
    )

    try:
        admin = await service.update_admin_role(
            admin_id=admin_id,
            role=role,
        )
        return admin

    except NotFoundError as e:
        logger.warning(
            "api_admin_not_found_for_role_update",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_admin_role_validation_error",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_admin_role_error",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث دور المدير",
        )


# ==============================================
# TOGGLE ADMIN STATUS
# ==============================================


@router.patch(
    "/{admin_id}/toggle-status",
    response_model=AdminResponse,
    summary="تبديل حالة المدير",
    description="تفعيل أو إلغاء تنشيط مدير",
)
async def toggle_admin_status(
    *,
    admin_id: int = Path(..., ge=1, description="معرف المدير"),
    service: AdminService = Depends(get_admin_service),
) -> AdminResponse:
    """
    تبديل حالة المدير (نشط/غير نشط).

    Args:
        admin_id: معرف المدير

    Returns:
        AdminResponse: المدير المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على المدير
    """
    logger.info(
        "api_toggle_admin_status",
        extra={"admin_id": admin_id},
    )

    try:
        admin = await service.toggle_admin_status(admin_id=admin_id)
        return admin

    except NotFoundError as e:
        logger.warning(
            "api_admin_not_found_for_status_toggle",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_toggle_admin_status_error",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تبديل حالة المدير",
        )


# ==============================================
# DELETE ADMIN
# ==============================================


@router.delete(
    "/{admin_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف مدير",
    description="حذف مدير موجود",
)
async def delete_admin(
    *,
    admin_id: int = Path(..., ge=1, description="معرف المدير"),
    permanent: bool = Query(False, description="حذف نهائي"),
    service: AdminService = Depends(get_admin_service),
) -> None:
    """
    حذف مدير.

    Args:
        admin_id: معرف المدير
        permanent: حذف نهائي

    Raises:
        HTTPException: إذا لم يتم العثور على المدير
    """
    logger.info(
        "api_delete_admin",
        extra={
            "admin_id": admin_id,
            "permanent": permanent,
        },
    )

    try:
        await service.delete_admin(
            admin_id=admin_id,
            permanent=permanent,
        )

    except NotFoundError as e:
        logger.warning(
            "api_admin_not_found_for_delete",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_delete_admin_validation_error",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_admin_error",
            extra={
                "admin_id": admin_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف المدير",
        )

    logger.info(
        "api_admin_deleted_successfully",
        extra={
            "admin_id": admin_id,
            "permanent": permanent,
        },
    )


# ==============================================
# GET ADMIN STATISTICS
# ==============================================


@router.get(
    "/statistics",
    response_model=AdminStatistics,
    summary="إحصائيات المديرين",
    description="الحصول على إحصائيات المديرين",
)
async def get_admin_statistics(
    *,
    service: AdminService = Depends(get_admin_service),
) -> AdminStatistics:
    """
    الحصول على إحصائيات المديرين.

    Returns:
        AdminStatistics: إحصائيات المديرين
    """
    logger.info("api_get_admin_statistics")

    try:
        stats = await service.get_admin_statistics()
        return AdminStatistics(
            total=stats["total"],
            active=stats["active"],
            inactive=stats["inactive"],
            roles=stats["roles"],
        )

    except Exception as e:
        logger.exception(
            "api_get_admin_statistics_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب إحصائيات المديرين",
        )
