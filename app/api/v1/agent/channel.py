# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📡 CHANNELS API
# نقاط نهاية API للقنوات (CRUD)
# تدير عمليات إنشاء واستعراض وتحديث وحذف القنوات
# ==============================================

"""MoulAI operational module for channel.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import Optional, Any, Dict

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
from app.schemas.agent import (
    ChannelCreate,
    ChannelResponse,
    ChannelUpdate,
    ChannelListResponse,
)
from app.services.business.agent.channel_service import ChannelService

# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/channels",
    tags=["📡 Channels"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================


async def get_channel_service(
    session: AsyncSession = Depends(get_db),
) -> ChannelService:
    """
    الحصول على خدمة القنوات.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        ChannelService: مثيل من ChannelService
    """
    return ChannelService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# CREATE CHANNEL
# ==============================================


@router.post(
    "/",
    response_model=ChannelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء قناة جديدة",
    description="إنشاء قناة جديدة في النظام",
)
async def create_channel(
    *,
    data: ChannelCreate,
    service: ChannelService = Depends(get_channel_service),
) -> ChannelResponse:
    """
    إنشاء قناة جديدة.

    Args:
        data: بيانات القناة

    Returns:
        ChannelResponse: القناة المنشأة

    Raises:
        HTTPException: إذا كانت القناة موجودة مسبقاً
    """
    logger.info(
        "api_create_channel",
        extra={
            "agent_id": data.agent_id,
            "type": data.type,
            "channel_name": data.name,
        },
    )

    try:
        channel = await service.create(channel_data=data)
        return channel

    except ConflictError as e:
        logger.warning(
            "api_create_channel_conflict",
            extra={
                "agent_id": data.agent_id,
                "type": data.type,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_channel_validation_error",
            extra={
                "agent_id": data.agent_id,
                "type": data.type,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_channel_error",
            extra={
                "agent_id": data.agent_id,
                "type": data.type,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء القناة",
        )


# ==============================================
# GET CHANNEL BY ID
# ==============================================


@router.get(
    "/{channel_id}",
    response_model=ChannelResponse,
    summary="الحصول على قناة بالمعرف",
    description="الحصول على قناة محددة بواسطة معرفها",
)
async def get_channel_by_id(
    *,
    channel_id: int = Path(..., ge=1, description="معرف القناة"),
    include_inactive: bool = Query(False, description="تضمين القنوات غير النشطة"),
    service: ChannelService = Depends(get_channel_service),
) -> ChannelResponse:
    """
    الحصول على قناة بالمعرف.

    Args:
        channel_id: معرف القناة
        include_inactive: تضمين القنوات غير النشطة

    Returns:
        ChannelResponse: القناة المطلوبة

    Raises:
        HTTPException: إذا لم يتم العثور على القناة
    """
    logger.info(
        "api_get_channel_by_id",
        extra={
            "channel_id": channel_id,
            "include_inactive": include_inactive,
        },
    )

    try:
        channel = await service.get_by_id(
            channel_id=channel_id,
            include_inactive=include_inactive,
        )
        return channel

    except NotFoundError as e:
        logger.warning(
            "api_channel_not_found",
            extra={
                "channel_id": channel_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_channel_by_id_error",
            extra={
                "channel_id": channel_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب القناة",
        )


# ==============================================
# LIST CHANNELS BY AGENT
# ==============================================


@router.get(
    "/agent/{agent_id}",
    response_model=ChannelListResponse,
    summary="قائمة قنوات وكيل",
    description="الحصول على قائمة القنوات لوكيل محدد",
)
async def list_channels_by_agent(
    *,
    agent_id: int = Path(..., ge=1, description="معرف الوكيل"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    only_active: bool = Query(True, description="جلب القنوات النشطة فقط"),
    service: ChannelService = Depends(get_channel_service),
) -> ChannelListResponse:
    """
    الحصول على قائمة قنوات وكيل معين.

    Args:
        agent_id: معرف الوكيل
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        only_active: جلب القنوات النشطة فقط

    Returns:
        ChannelListResponse: قائمة القنوات مع الإحصائيات
    """
    logger.info(
        "api_list_channels_by_agent",
        extra={
            "agent_id": agent_id,
            "skip": skip,
            "limit": limit,
            "only_active": only_active,
        },
    )

    try:
        return await service.get_by_agent(
            agent_id=agent_id,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

    except NotFoundError as e:
        logger.warning(
            "api_agent_not_found_for_channels",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_list_channels_by_agent_error",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة القنوات",
        )


# ==============================================
# GET CHANNEL BY TYPE
# ==============================================


@router.get(
    "/type",
    response_model=Optional[ChannelResponse],
    summary="الحصول على قناة حسب النوع",
    description="الحصول على قناة محددة حسب نوعها",
)
async def get_channel_by_type(
    *,
    agent_id: int = Query(..., ge=1, description="معرف الوكيل"),
    channel_type: str = Query(..., description="نوع القناة"),
    only_active: bool = Query(True, description="جلب القناة النشطة فقط"),
    service: ChannelService = Depends(get_channel_service),
) -> Optional[ChannelResponse]:
    """
    الحصول على قناة حسب النوع.

    Args:
        agent_id: معرف الوكيل
        channel_type: نوع القناة
        only_active: جلب القناة النشطة فقط

    Returns:
        Optional[ChannelResponse]: القناة المطلوبة أو None
    """
    logger.info(
        "api_get_channel_by_type",
        extra={
            "agent_id": agent_id,
            "channel_type": channel_type,
            "only_active": only_active,
        },
    )

    try:
        return await service.get_by_type(
            agent_id=agent_id,
            channel_type=channel_type,
            only_active=only_active,
        )

    except Exception as e:
        logger.exception(
            "api_get_channel_by_type_error",
            extra={
                "agent_id": agent_id,
                "channel_type": channel_type,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب القناة حسب النوع",
        )


# ==============================================
# SEARCH CHANNELS
# ==============================================


@router.get(
    "/search",
    response_model=ChannelListResponse,
    summary="البحث عن القنوات",
    description="البحث عن القنوات باستخدام كلمات مفتاحية",
)
async def search_channels(
    *,
    query: str = Query(..., min_length=1, max_length=100, description="نص البحث"),
    agent_id: Optional[int] = Query(None, ge=1, description="معرف الوكيل (اختياري)"),
    only_active: bool = Query(True, description="جلب القنوات النشطة فقط"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: ChannelService = Depends(get_channel_service),
) -> ChannelListResponse:
    """
    البحث عن القنوات.

    Args:
        query: نص البحث
        agent_id: معرف الوكيل (اختياري)
        only_active: جلب القنوات النشطة فقط
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        ChannelListResponse: قائمة القنوات مع الإحصائيات
    """
    logger.info(
        "api_search_channels",
        extra={
            "query": query,
            "agent_id": agent_id,
            "only_active": only_active,
        },
    )

    try:
        return await service.search(
            query=query,
            agent_id=agent_id,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_search_channels_error",
            extra={
                "query": query,
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء البحث عن القنوات",
        )


# ==============================================
# UPDATE CHANNEL
# ==============================================


@router.patch(
    "/{channel_id}",
    response_model=ChannelResponse,
    summary="تحديث قناة",
    description="تحديث بيانات قناة موجودة",
)
async def update_channel(
    *,
    channel_id: int = Path(..., ge=1, description="معرف القناة"),
    data: ChannelUpdate,
    service: ChannelService = Depends(get_channel_service),
) -> ChannelResponse:
    """
    تحديث قناة موجودة.

    Args:
        channel_id: معرف القناة
        data: بيانات التحديث

    Returns:
        ChannelResponse: القناة المحدثة

    Raises:
        HTTPException: إذا لم يتم العثور على القناة
    """
    logger.info(
        "api_update_channel",
        extra={
            "channel_id": channel_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        channel = await service.update(
            channel_id=channel_id,
            update_data=data,
        )
        return channel

    except NotFoundError as e:
        logger.warning(
            "api_channel_not_found_for_update",
            extra={
                "channel_id": channel_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_channel_validation_error",
            extra={
                "channel_id": channel_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_channel_error",
            extra={
                "channel_id": channel_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث القناة",
        )


# ==============================================
# UPDATE CHANNEL CONFIG
# ==============================================


@router.patch(
    "/{channel_id}/config",
    response_model=ChannelResponse,
    summary="تحديث إعدادات القناة",
    description="تحديث إعدادات قناة موجودة",
)
async def update_channel_config(
    *,
    channel_id: int = Path(..., ge=1, description="معرف القناة"),
    config: Dict[str, Any],
    service: ChannelService = Depends(get_channel_service),
) -> ChannelResponse:
    """
    تحديث إعدادات القناة.

    Args:
        channel_id: معرف القناة
        config: إعدادات القناة الجديدة

    Returns:
        ChannelResponse: القناة المحدثة

    Raises:
        HTTPException: إذا لم يتم العثور على القناة
    """
    logger.info(
        "api_update_channel_config",
        extra={
            "channel_id": channel_id,
        },
    )

    try:
        channel = await service.update_config(
            channel_id=channel_id,
            config=config,
        )
        return channel

    except NotFoundError as e:
        logger.warning(
            "api_channel_not_found_for_config_update",
            extra={
                "channel_id": channel_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_channel_config_error",
            extra={
                "channel_id": channel_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث إعدادات القناة",
        )


# ==============================================
# TOGGLE CHANNEL STATUS
# ==============================================


@router.patch(
    "/{channel_id}/toggle-status",
    response_model=ChannelResponse,
    summary="تبديل حالة القناة",
    description="تفعيل أو إلغاء تنشيط قناة",
)
async def toggle_channel_status(
    *,
    channel_id: int = Path(..., ge=1, description="معرف القناة"),
    service: ChannelService = Depends(get_channel_service),
) -> ChannelResponse:
    """
    تبديل حالة القناة (نشط/غير نشط).

    Args:
        channel_id: معرف القناة

    Returns:
        ChannelResponse: القناة المحدثة

    Raises:
        HTTPException: إذا لم يتم العثور على القناة
    """
    logger.info(
        "api_toggle_channel_status",
        extra={"channel_id": channel_id},
    )

    try:
        channel = await service.toggle_active(channel_id=channel_id)
        return channel

    except NotFoundError as e:
        logger.warning(
            "api_channel_not_found_for_status_toggle",
            extra={
                "channel_id": channel_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_toggle_channel_status_error",
            extra={
                "channel_id": channel_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تبديل حالة القناة",
        )


# ==============================================
# DELETE CHANNEL
# ==============================================


@router.delete(
    "/{channel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف قناة",
    description="حذف قناة موجودة",
)
async def delete_channel(
    *,
    channel_id: int = Path(..., ge=1, description="معرف القناة"),
    permanent: bool = Query(False, description="حذف نهائي"),
    service: ChannelService = Depends(get_channel_service),
) -> None:
    """
    حذف قناة.

    Args:
        channel_id: معرف القناة
        permanent: حذف نهائي

    Raises:
        HTTPException: إذا لم يتم العثور على القناة
    """
    logger.info(
        "api_delete_channel",
        extra={
            "channel_id": channel_id,
            "permanent": permanent,
        },
    )

    try:
        await service.delete(
            channel_id=channel_id,
            permanent=permanent,
        )

    except NotFoundError as e:
        logger.warning(
            "api_channel_not_found_for_delete",
            extra={
                "channel_id": channel_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_delete_channel_validation_error",
            extra={
                "channel_id": channel_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_channel_error",
            extra={
                "channel_id": channel_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف القناة",
        )

    logger.info(
        "api_channel_deleted_successfully",
        extra={
            "channel_id": channel_id,
            "permanent": permanent,
        },
    )


# ==============================================
# DELETE CHANNELS BY AGENT
# ==============================================


@router.delete(
    "/agent/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف قنوات وكيل",
    description="حذف جميع قنوات وكيل محدد",
)
async def delete_channels_by_agent(
    *,
    agent_id: int = Path(..., ge=1, description="معرف الوكيل"),
    permanent: bool = Query(False, description="حذف نهائي"),
    service: ChannelService = Depends(get_channel_service),
) -> None:
    """
    حذف جميع قنوات وكيل معين.

    Args:
        agent_id: معرف الوكيل
        permanent: حذف نهائي

    Raises:
        HTTPException: إذا لم يتم العثور على الوكيل
    """
    logger.info(
        "api_delete_channels_by_agent",
        extra={
            "agent_id": agent_id,
            "permanent": permanent,
        },
    )

    try:
        count = await service.delete_by_agent(
            agent_id=agent_id,
            permanent=permanent,
        )
        logger.info(
            "api_channels_deleted_by_agent_successfully",
            extra={
                "agent_id": agent_id,
                "deleted_count": count,
                "permanent": permanent,
            },
        )

    except NotFoundError as e:
        logger.warning(
            "api_agent_not_found_for_channels_delete",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_channels_by_agent_error",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف قنوات الوكيل",
        )


# ==============================================
# GET CHANNEL STATISTICS
# ==============================================


@router.get(
    "/statistics/{agent_id}",
    response_model=Dict[str, Any],
    summary="إحصائيات القنوات",
    description="الحصول على إحصائيات القنوات لوكيل محدد",
)
async def get_channel_statistics(
    *,
    agent_id: int = Path(..., ge=1, description="معرف الوكيل"),
    service: ChannelService = Depends(get_channel_service),
) -> Dict[str, Any]:
    """
    الحصول على إحصائيات القنوات لوكيل معين.

    Args:
        agent_id: معرف الوكيل

    Returns:
        Dict[str, Any]: إحصائيات القنوات
    """
    logger.info(
        "api_get_channel_statistics",
        extra={"agent_id": agent_id},
    )

    try:
        return await service.get_statistics(agent_id=agent_id)

    except NotFoundError as e:
        logger.warning(
            "api_agent_not_found_for_statistics",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_channel_statistics_error",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب إحصائيات القنوات",
        )
