# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / API / V1 / USER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for user.

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
)

from app.core.database import get_db
from app.core.logger import logger
from app.schemas.user import (
    ConsentResponse,
    UserConsentUpdate,
    UserCreate,
    UserResponse,
    UserSearch,
    UserSummary,
    UserUpdate,
    UserListResponse,
)
from app.services.business.user_service import UserService

# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================


async def get_user_service(
    session: AsyncSession = Depends(get_db),
) -> UserService:
    """
    الحصول على خدمة المستخدمين.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        UserService: مثيل من UserService
    """
    return UserService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# LIST USERS
# ==============================================


@router.get(
    "/",
    response_model=UserListResponse,
    summary="قائمة المستخدمين",
    description="الحصول على قائمة المستخدمين مع إمكانية التصفية",
)
async def list_users(
    *,
    has_consent: Optional[bool] = Query(
        None,
        description="تصفية حسب حالة الموافقة",
    ),
    search: Optional[str] = Query(
        None,
        min_length=1,
        max_length=255,
        description="نص البحث (الاسم أو رقم الهاتف)",
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
    service: UserService = Depends(get_user_service),
) -> UserListResponse:
    """
    الحصول على قائمة المستخدمين.

    Args:
        has_consent: تصفية حسب حالة الموافقة
        search: نص البحث
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة المستخدمين

    Returns:
        UserListResponse: قائمة المستخدمين مع الإحصائيات
    """
    logger.info(
        "api_list_users",
        extra={
            "has_consent": has_consent,
            "search": search,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        if search is not None:
            # استخدام طريقة البحث
            users = await service.search_by_name(
                name=search,
                skip=skip,
                limit=limit,
            )
            total = len(users)

        elif has_consent is not None:
            users = await service.get_by_consent(
                has_consent=has_consent,
                skip=skip,
                limit=limit,
            )
            total = len(users)

        else:
            users = await service.repo.get_all(
                skip=skip,
                limit=limit,
                order_by="created_at",
                descending=True,
            )
            total = await service.repo.count()

        return UserListResponse(
            items=[UserResponse.model_validate(user) for user in users],
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_list_users_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة المستخدمين",
        )


# ==============================================
# GET USER BY ID
# ==============================================


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="مستخدم بالمعرف",
    description="الحصول على مستخدم محدد",
)
async def get_user(
    *,
    user_id: int = Path(..., ge=1, description="معرف المستخدم"),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    الحصول على مستخدم بالمعرف.

    Args:
        user_id: معرف المستخدم
        service: خدمة المستخدمين

    Returns:
        UserResponse: المستخدم المطلوب

    Raises:
        HTTPException: إذا لم يتم العثور على المستخدم
    """
    logger.info(
        "api_get_user",
        extra={"user_id": user_id},
    )

    try:
        user = await service.get_by_id(
            user_id=user_id,
        )
        return user

    except NotFoundError as e:
        logger.warning(
            "api_user_not_found",
            extra={
                "user_id": user_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_user_error",
            extra={
                "user_id": user_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب المستخدم",
        )


# ==============================================
# GET USER BY CHAT ID
# ==============================================


@router.get(
    "/chat/{chat_id}",
    response_model=UserResponse,
    summary="مستخدم بواسطة chat_id",
    description="الحصول على مستخدم بواسطة معرف تيليجرام",
)
async def get_user_by_chat_id(
    *,
    chat_id: int = Path(..., ge=1, description="معرف المستخدم في تيليجرام"),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    الحصول على مستخدم بواسطة معرف تيليجرام.

    Args:
        chat_id: معرف المستخدم في تيليجرام
        service: خدمة المستخدمين

    Returns:
        UserResponse: المستخدم المطلوب

    Raises:
        HTTPException: إذا لم يتم العثور على المستخدم
    """
    logger.info(
        "api_get_user_by_chat_id",
        extra={"chat_id": chat_id},
    )

    try:
        user = await service.get_by_chat_id(
            chat_id=chat_id,
        )

        if not user:
            raise NotFoundError(
                message=f"المستخدم بـ chat_id '{chat_id}' غير موجود",
            )

        return user

    except NotFoundError as e:
        logger.warning(
            "api_user_not_found_by_chat_id",
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
            "api_get_user_by_chat_id_error",
            extra={
                "chat_id": chat_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب المستخدم",
        )


# ==============================================
# CREATE USER
# ==============================================


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء مستخدم",
    description="إنشاء مستخدم جديد",
)
async def create_user(
    *,
    data: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    إنشاء مستخدم جديد.

    Args:
        data: بيانات المستخدم
        service: خدمة المستخدمين

    Returns:
        UserResponse: المستخدم المنشأ

    Raises:
        HTTPException: إذا حدث خطأ أثناء الإنشاء
    """
    logger.info(
        "api_create_user",
        extra={
            "chat_id": data.chat_id,
            "customer_name": data.customer_name,
        },
    )

    try:
        user = await service.create_user(
            user_data=data,
        )
        return user

    except ConflictError as e:
        logger.warning(
            "api_create_user_conflict",
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
            "api_create_user_validation_error",
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
        logger.exception(
            "api_create_user_error",
            extra={
                "chat_id": data.chat_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء المستخدم",
        )


# ==============================================
# UPDATE USER
# ==============================================


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="تحديث مستخدم",
    description="تحديث مستخدم موجود",
)
async def update_user(
    *,
    user_id: int = Path(..., ge=1, description="معرف المستخدم"),
    data: UserUpdate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    تحديث مستخدم موجود.

    Args:
        user_id: معرف المستخدم
        data: بيانات التحديث
        service: خدمة المستخدمين

    Returns:
        UserResponse: المستخدم المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على المستخدم
    """
    logger.info(
        "api_update_user",
        extra={
            "user_id": user_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        # التحقق من وجود المستخدم
        existing = await service.get_by_id(
            user_id=user_id,
        )

        # تحديث المستخدم
        user = await service.update_user(
            chat_id=existing.chat_id,
            update_data=data,
        )
        return user

    except NotFoundError as e:
        logger.warning(
            "api_user_not_found_for_update",
            extra={
                "user_id": user_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_user_validation_error",
            extra={
                "user_id": user_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_user_error",
            extra={
                "user_id": user_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث المستخدم",
        )


# ==============================================
# UPDATE USER CONSENT
# ==============================================


@router.patch(
    "/chat/{chat_id}/consent",
    response_model=ConsentResponse,
    summary="تحديث موافقة المستخدم",
    description="منح أو إلغاء موافقة المستخدم",
)
async def update_user_consent(
    *,
    chat_id: int = Path(..., ge=1, description="معرف المستخدم في تيليجرام"),
    data: UserConsentUpdate,
    service: UserService = Depends(get_user_service),
) -> ConsentResponse:
    """
    تحديث موافقة المستخدم.

    Args:
        chat_id: معرف المستخدم في تيليجرام
        data: بيانات تحديث الموافقة
        service: خدمة المستخدمين

    Returns:
        ConsentResponse: حالة الموافقة المحدثة

    Raises:
        HTTPException: إذا لم يتم العثور على المستخدم
    """
    logger.info(
        "api_update_user_consent",
        extra={
            "chat_id": chat_id,
            "consent": data.consent,
        },
    )

    try:
        user = await service.update_consent(
            chat_id=chat_id,
            consent_data=data,
        )

        return ConsentResponse(
            chat_id=chat_id,
            has_consent=user.consent,
            message=f"تم {'منح' if user.consent else 'إلغاء'} الموافقة بنجاح",
        )

    except NotFoundError as e:
        logger.warning(
            "api_user_not_found_for_consent",
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
            "api_update_user_consent_error",
            extra={
                "chat_id": chat_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث موافقة المستخدم",
        )


# ==============================================
# CHECK USER CONSENT
# ==============================================


@router.get(
    "/chat/{chat_id}/consent",
    response_model=ConsentResponse,
    summary="التحقق من موافقة المستخدم",
    description="التحقق مما إذا كان المستخدم قد أعطى موافقته",
)
async def check_user_consent(
    *,
    chat_id: int = Path(..., ge=1, description="معرف المستخدم في تيليجرام"),
    service: UserService = Depends(get_user_service),
) -> ConsentResponse:
    """
    التحقق من موافقة المستخدم.

    Args:
        chat_id: معرف المستخدم في تيليجرام
        service: خدمة المستخدمين

    Returns:
        ConsentResponse: حالة الموافقة
    """
    logger.info(
        "api_check_user_consent",
        extra={"chat_id": chat_id},
    )

    try:
        has_consent = await service.has_consent(
            chat_id=chat_id,
        )

        return ConsentResponse(
            chat_id=chat_id,
            has_consent=has_consent,
            message=(
                "المستخدم لديه موافقة" if has_consent else "المستخدم ليس لديه موافقة"
            ),
        )

    except Exception as e:
        logger.exception(
            "api_check_user_consent_error",
            extra={
                "chat_id": chat_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء التحقق من موافقة المستخدم",
        )


# ==============================================
# SEARCH USERS
# ==============================================


@router.post(
    "/search",
    response_model=UserListResponse,
    summary="بحث عن مستخدمين",
    description="البحث عن مستخدمين بالاسم أو رقم الهاتف",
)
async def search_users(
    *,
    data: UserSearch,
    service: UserService = Depends(get_user_service),
) -> UserListResponse:
    """
    البحث عن مستخدمين.

    Args:
        data: بيانات البحث
        service: خدمة المستخدمين

    Returns:
        UserListResponse: قائمة المستخدمين المطابقين للبحث مع الإحصائيات
    """
    logger.info(
        "api_search_users",
        extra={
            "query": data.query,
            "skip": data.skip,
            "limit": data.limit,
        },
    )

    try:
        result = await service.search(
            search_params=data,
        )
        return result

    except Exception as e:
        logger.exception(
            "api_search_users_error",
            extra={
                "query": data.query,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء البحث عن المستخدمين",
        )


# ==============================================
# GET USER SUMMARY
# ==============================================


@router.get(
    "/stats/summary",
    response_model=UserSummary,
    summary="ملخص المستخدمين",
    description="الحصول على ملخص إحصائيات المستخدمين",
)
async def get_user_summary(
    *,
    service: UserService = Depends(get_user_service),
) -> UserSummary:
    """
    الحصول على ملخص إحصائيات المستخدمين.

    Args:
        service: خدمة المستخدمين

    Returns:
        UserSummary: ملخص إحصائيات المستخدمين
    """
    logger.info("api_get_user_summary")

    try:
        summary = await service.get_user_stats()
        return summary

    except Exception as e:
        logger.exception(
            "api_get_user_summary_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب ملخص المستخدمين",
        )


# ==============================================
# DELETE USER
# ==============================================


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف مستخدم",
    description="حذف مستخدم موجود",
)
async def delete_user(
    *,
    user_id: int = Path(..., ge=1, description="معرف المستخدم"),
    service: UserService = Depends(get_user_service),
) -> None:
    """
    حذف مستخدم موجود.

    Args:
        user_id: معرف المستخدم
        service: خدمة المستخدمين

    Raises:
        HTTPException: إذا لم يتم العثور على المستخدم
    """
    logger.info(
        "api_delete_user",
        extra={"user_id": user_id},
    )

    try:
        # التحقق من وجود المستخدم
        user = await service.get_by_id(
            user_id=user_id,
        )

        # حذف المستخدم
        await service.delete_user(
            chat_id=user.chat_id,
        )

    except NotFoundError as e:
        logger.warning(
            "api_user_not_found_for_delete",
            extra={
                "user_id": user_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_user_error",
            extra={
                "user_id": user_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف المستخدم",
        )

    logger.info(
        "api_user_deleted_successfully",
        extra={"user_id": user_id},
    )
