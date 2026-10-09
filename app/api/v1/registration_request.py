# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / API / V1 / REGISTRATION REQUEST
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for registration request.

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
from app.schemas.registration_request import (
    RegistrationRequestCreate,
    RegistrationRequestResponse,
    RegistrationRequestUpdate,
    RegistrationRequestStatusUpdate,
    RegistrationRequestListResponse,
)
from app.services.business.registration_request_service import (
    RegistrationRequestService,
)

# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/registration-requests",
    tags=["Registration Requests"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================


async def get_registration_request_service(
    session: AsyncSession = Depends(get_db),
) -> RegistrationRequestService:
    """
    الحصول على خدمة طلبات التسجيل.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        RegistrationRequestService: مثيل من RegistrationRequestService
    """
    return RegistrationRequestService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# LIST REGISTRATION REQUESTS
# ==============================================


@router.get(
    "/",
    response_model=RegistrationRequestListResponse,
    summary="قائمة طلبات التسجيل",
    description="الحصول على قائمة طلبات التسجيل مع إمكانية التصفية",
)
async def list_registration_requests(
    *,
    status: Optional[str] = Query(
        None,
        description="حالة الطلب (pending, approved, rejected)",
        min_length=1,
        max_length=50,
    ),
    chat_id: Optional[int] = Query(
        None,
        description="معرف المستخدم في تيليجرام",
        ge=1,
    ),
    search: Optional[str] = Query(
        None,
        min_length=1,
        max_length=255,
        description="نص البحث (اسم المطعم أو الاسم الكامل)",
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
    service: RegistrationRequestService = Depends(
        get_registration_request_service,
    ),
) -> RegistrationRequestListResponse:
    """
    الحصول على قائمة طلبات التسجيل.

    Args:
        status: حالة الطلب للتصفية
        chat_id: معرف المستخدم للتصفية
        search: نص البحث
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        service: خدمة طلبات التسجيل

    Returns:
        RegistrationRequestListResponse: قائمة طلبات التسجيل مع الإحصائيات
    """
    logger.info(
        "api_list_registration_requests",
        extra={
            "status": status,
            "chat_id": chat_id,
            "search": search,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        # تحديد طريقة الجلب بناءً على معايير التصفية
        if chat_id is not None:
            request_obj = await service.get_by_chat_id(chat_id=chat_id)
            if request_obj:
                requests = [request_obj]
                total = 1
            else:
                requests = []
                total = 0
        elif search is not None:
            requests = await service.search(
                query=search,
                skip=skip,
                limit=limit,
            )
            total = len(requests)
        elif status is not None:
            requests = await service.get_by_status(
                status=status,
                skip=skip,
                limit=limit,
            )
            total = await service.count_by_status(status=status)
        else:
            requests = await service.get_all(
                skip=skip,
                limit=limit,
            )
            # حساب العدد الإجمالي (يمكن تحسينه بإضافة دالة count_all)
            total = len(requests)

        return RegistrationRequestListResponse(
            items=requests,
            total=total,
            skip=skip,
            limit=limit,
        )

    except ValidationError as e:
        logger.warning(
            "api_list_registration_requests_validation_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_list_registration_requests_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة طلبات التسجيل",
        )


# ==============================================
# GET REGISTRATION REQUEST BY ID
# ==============================================


@router.get(
    "/{request_id}",
    response_model=RegistrationRequestResponse,
    summary="طلب تسجيل بالمعرف",
    description="الحصول على طلب تسجيل محدد",
)
async def get_registration_request(
    *,
    request_id: int = Path(..., ge=1, description="معرف طلب التسجيل"),
    service: RegistrationRequestService = Depends(
        get_registration_request_service,
    ),
) -> RegistrationRequestResponse:
    """
    الحصول على طلب تسجيل بالمعرف.

    Args:
        request_id: معرف طلب التسجيل
        service: خدمة طلبات التسجيل

    Returns:
        RegistrationRequestResponse: طلب التسجيل المطلوب

    Raises:
        HTTPException: إذا لم يتم العثور على الطلب
    """
    logger.info(
        "api_get_registration_request",
        extra={"request_id": request_id},
    )

    try:
        request_obj = await service.get_by_id(
            request_id=request_id,
        )
        return request_obj

    except NotFoundError as e:
        logger.warning(
            "api_registration_request_not_found",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_registration_request_error",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب طلب التسجيل",
        )


# ==============================================
# GET REGISTRATION REQUEST BY CHAT ID
# ==============================================


@router.get(
    "/chat/{chat_id}",
    response_model=RegistrationRequestResponse,
    summary="طلب تسجيل بـ chat_id",
    description="الحصول على طلب تسجيل بواسطة chat_id",
)
async def get_registration_request_by_chat_id(
    *,
    chat_id: int = Path(..., ge=1, description="معرف المستخدم في تيليجرام"),
    service: RegistrationRequestService = Depends(
        get_registration_request_service,
    ),
) -> RegistrationRequestResponse:
    """
    الحصول على طلب تسجيل بواسطة chat_id.

    Args:
        chat_id: معرف المستخدم في تيليجرام
        service: خدمة طلبات التسجيل

    Returns:
        RegistrationRequestResponse: طلب التسجيل

    Raises:
        HTTPException: إذا لم يتم العثور على الطلب
    """
    logger.info(
        "api_get_registration_request_by_chat_id",
        extra={"chat_id": chat_id},
    )

    try:
        request_obj = await service.get_by_chat_id(chat_id=chat_id)

        if not request_obj:
            raise NotFoundError(
                message=f"طلب التسجيل بـ chat_id '{chat_id}' غير موجود",
            )

        return request_obj

    except NotFoundError as e:
        logger.warning(
            "api_registration_request_not_found_by_chat_id",
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
            "api_get_registration_request_by_chat_id_error",
            extra={
                "chat_id": chat_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب طلب التسجيل",
        )


# ==============================================
# CREATE REGISTRATION REQUEST
# ==============================================


@router.post(
    "/",
    response_model=RegistrationRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء طلب تسجيل",
    description="إنشاء طلب تسجيل جديد",
)
async def create_registration_request(
    *,
    data: RegistrationRequestCreate,
    service: RegistrationRequestService = Depends(
        get_registration_request_service,
    ),
) -> RegistrationRequestResponse:
    """
    إنشاء طلب تسجيل جديد.

    Args:
        data: بيانات طلب التسجيل
        service: خدمة طلبات التسجيل

    Returns:
        RegistrationRequestResponse: طلب التسجيل المنشأ

    Raises:
        HTTPException: إذا حدث خطأ أثناء الإنشاء
    """
    logger.info(
        "api_create_registration_request",
        extra={
            "chat_id": data.chat_id,
            "restaurant_name": data.restaurant_name,
        },
    )

    try:
        request_obj = await service.create(
            request_data=data,
        )
        return request_obj

    except ConflictError as e:
        logger.warning(
            "api_create_registration_request_conflict",
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
            "api_create_registration_request_validation_error",
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
            "api_create_registration_request_error",
            extra={
                "chat_id": data.chat_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء طلب التسجيل",
        )


# ==============================================
# UPDATE REGISTRATION REQUEST
# ==============================================


@router.patch(
    "/{request_id}",
    response_model=RegistrationRequestResponse,
    summary="تحديث طلب تسجيل",
    description="تحديث طلب تسجيل موجود",
)
async def update_registration_request(
    *,
    request_id: int = Path(..., ge=1, description="معرف طلب التسجيل"),
    data: RegistrationRequestUpdate,
    service: RegistrationRequestService = Depends(
        get_registration_request_service,
    ),
) -> RegistrationRequestResponse:
    """
    تحديث طلب تسجيل موجود.

    Args:
        request_id: معرف طلب التسجيل
        data: بيانات التحديث
        service: خدمة طلبات التسجيل

    Returns:
        RegistrationRequestResponse: طلب التسجيل المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على الطلب أو حدث تعارض
    """
    logger.info(
        "api_update_registration_request",
        extra={
            "request_id": request_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        request_obj = await service.update(
            request_id=request_id,
            update_data=data,
        )
        return request_obj

    except NotFoundError as e:
        logger.warning(
            "api_registration_request_not_found_for_update",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_registration_request_validation_error",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_registration_request_error",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث طلب التسجيل",
        )


# ==============================================
# UPDATE REGISTRATION REQUEST STATUS
# ==============================================


@router.patch(
    "/{request_id}/status",
    response_model=RegistrationRequestResponse,
    summary="تغيير حالة طلب التسجيل",
    description="تغيير حالة طلب التسجيل (approve/reject)",
)
async def update_registration_request_status(
    *,
    request_id: int = Path(..., ge=1, description="معرف طلب التسجيل"),
    data: RegistrationRequestStatusUpdate,
    owner_id: Optional[int] = Query(
        None,
        description="معرف المالك (عند الموافقة)",
        ge=1,
    ),
    service: RegistrationRequestService = Depends(
        get_registration_request_service,
    ),
) -> RegistrationRequestResponse:
    """
    تغيير حالة طلب التسجيل.

    Args:
        request_id: معرف طلب التسجيل
        data: بيانات تحديث الحالة
        owner_id: معرف المالك (عند الموافقة)
        service: خدمة طلبات التسجيل

    Returns:
        RegistrationRequestResponse: طلب التسجيل المحدث

    Raises:
        HTTPException: إذا كانت الحالة غير صالحة أو لم يتم العثور على الطلب
    """
    logger.info(
        "api_update_registration_request_status",
        extra={
            "request_id": request_id,
            "status": data.status,
            "owner_id": owner_id,
        },
    )

    try:
        # إذا كانت الحالة approved، نستخدم approve مع owner_id
        if data.status == "approved":
            request_obj = await service.approve(
                request_id=request_id,
                owner_id=owner_id,
            )
        else:
            request_obj = await service.reject(
                request_id=request_id,
            )
        return request_obj

    except NotFoundError as e:
        logger.warning(
            "api_registration_request_not_found_for_status_update",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_registration_request_status_validation_error",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_registration_request_status_error",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث حالة طلب التسجيل",
        )


# ==============================================
# APPROVE REGISTRATION REQUEST
# ==============================================


@router.post(
    "/{request_id}/approve",
    response_model=RegistrationRequestResponse,
    summary="اعتماد طلب التسجيل",
    description="اعتماد طلب التسجيل وإنشاء المالك والمطعم والاشتراك",
)
async def approve_registration_request(
    *,
    request_id: int = Path(..., ge=1, description="معرف طلب التسجيل"),
    owner_id: Optional[int] = Query(
        None,
        description="معرف المالك (اختياري - إذا كان المالك موجوداً مسبقاً)",
        ge=1,
    ),
    service: RegistrationRequestService = Depends(
        get_registration_request_service,
    ),
) -> RegistrationRequestResponse:
    """
    اعتماد طلب التسجيل.

    Args:
        request_id: معرف طلب التسجيل
        owner_id: معرف المالك (اختياري)
        service: خدمة طلبات التسجيل

    Returns:
        RegistrationRequestResponse: طلب التسجيل المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على الطلب
    """
    logger.info(
        "api_approve_registration_request",
        extra={
            "request_id": request_id,
            "owner_id": owner_id,
        },
    )

    try:
        request_obj = await service.approve(
            request_id=request_id,
            owner_id=owner_id,
        )
        return request_obj

    except NotFoundError as e:
        logger.warning(
            "api_registration_request_not_found_for_approve",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_approve_registration_request_validation_error",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_approve_registration_request_error",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء اعتماد طلب التسجيل",
        )


# ==============================================
# REJECT REGISTRATION REQUEST
# ==============================================


@router.post(
    "/{request_id}/reject",
    response_model=RegistrationRequestResponse,
    summary="رفض طلب التسجيل",
    description="رفض طلب التسجيل",
)
async def reject_registration_request(
    *,
    request_id: int = Path(..., ge=1, description="معرف طلب التسجيل"),
    service: RegistrationRequestService = Depends(
        get_registration_request_service,
    ),
) -> RegistrationRequestResponse:
    """
    رفض طلب التسجيل.

    Args:
        request_id: معرف طلب التسجيل
        service: خدمة طلبات التسجيل

    Returns:
        RegistrationRequestResponse: طلب التسجيل المحدث

    Raises:
        HTTPException: إذا لم يتم العثور على الطلب
    """
    logger.info(
        "api_reject_registration_request",
        extra={"request_id": request_id},
    )

    try:
        request_obj = await service.reject(
            request_id=request_id,
        )
        return request_obj

    except NotFoundError as e:
        logger.warning(
            "api_registration_request_not_found_for_reject",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_reject_registration_request_validation_error",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_reject_registration_request_error",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء رفض طلب التسجيل",
        )


# ==============================================
# DELETE REGISTRATION REQUEST
# ==============================================


@router.delete(
    "/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف طلب تسجيل",
    description="حذف طلب تسجيل موجود",
)
async def delete_registration_request(
    *,
    request_id: int = Path(..., ge=1, description="معرف طلب التسجيل"),
    service: RegistrationRequestService = Depends(
        get_registration_request_service,
    ),
) -> None:
    """
    حذف طلب تسجيل.

    Args:
        request_id: معرف طلب التسجيل
        service: خدمة طلبات التسجيل

    Raises:
        HTTPException: إذا لم يتم العثور على الطلب
    """
    logger.info(
        "api_delete_registration_request",
        extra={"request_id": request_id},
    )

    try:
        await service.delete(
            request_id=request_id,
        )

    except NotFoundError as e:
        logger.warning(
            "api_registration_request_not_found_for_delete",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_delete_registration_request_validation_error",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_registration_request_error",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف طلب التسجيل",
        )

    logger.info(
        "api_registration_request_deleted_successfully",
        extra={"request_id": request_id},
    )


# ==============================================
# GET REGISTRATION REQUESTS SUMMARY
# ==============================================


@router.get(
    "/stats/summary",
    summary="ملخص طلبات التسجيل",
    description="الحصول على ملخص طلبات التسجيل",
)
async def get_registration_requests_summary(
    *,
    service: RegistrationRequestService = Depends(
        get_registration_request_service,
    ),
) -> dict:
    """
    الحصول على ملخص طلبات التسجيل.

    Args:
        service: خدمة طلبات التسجيل

    Returns:
        dict: ملخص طلبات التسجيل
    """
    logger.info("api_get_registration_requests_summary")

    try:
        total = len(await service.get_all(limit=1000))
        pending = await service.count_pending()
        approved = await service.count_by_status(status="approved")
        rejected = await service.count_by_status(status="rejected")

        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
        }

    except Exception as e:
        logger.exception(
            "api_get_registration_requests_summary_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب ملخص طلبات التسجيل",
        )
