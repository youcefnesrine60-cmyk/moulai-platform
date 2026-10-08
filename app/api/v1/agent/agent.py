# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🤖 AGENTS API
# نقاط نهاية API للوكلاء (CRUD)
# تدير عمليات إنشاء واستعراض وتحديث وحذف الوكلاء
# ==============================================

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
from app.schemas.agent import (
    AgentCreate,
    AgentResponse,
    AgentUpdate,
    AgentListResponse,
    AgentStatistics,
    AgentConfigUpdate,
)
from app.services.business.agent.agent_service import AgentService


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/agents",
    tags=["🤖 Agents"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================

async def get_agent_service(
    session: AsyncSession = Depends(get_db),
) -> AgentService:
    """
    الحصول على خدمة الوكلاء.
    
    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        AgentService: مثيل من AgentService
    """
    return AgentService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# CREATE AGENT
# ==============================================

@router.post(
    "/",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء وكيل جديد",
    description="إنشاء وكيل ذكي جديد في النظام",
)
async def create_agent(
    *,
    data: AgentCreate,
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """
    إنشاء وكيل جديد.
    
    Args:
        data: بيانات الوكيل
        
    Returns:
        AgentResponse: الوكيل المنشأ
        
    Raises:
        HTTPException: إذا كان الاسم موجوداً مسبقاً
    """
    logger.info(
        "api_create_agent",
        extra={
            "restaurant_id": data.restaurant_id,
            "agent_name": data.name,
        },
    )

    try:
        agent = await service.create(agent_data=data)
        return agent

    except ConflictError as e:
        logger.warning(
            "api_create_agent_conflict",
            extra={
                "restaurant_id": data.restaurant_id,
                "agent_name": data.name,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_agent_validation_error",
            extra={
                "restaurant_id": data.restaurant_id,
                "agent_name": data.name,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_agent_error",
            extra={
                "restaurant_id": data.restaurant_id,
                "agent_name": data.name,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء الوكيل",
        )


# ==============================================
# GET AGENT BY ID
# ==============================================

@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="الحصول على وكيل بالمعرف",
    description="الحصول على وكيل محدد بواسطة معرفه",
)
async def get_agent_by_id(
    *,
    agent_id: int = Path(..., ge=1, description="معرف الوكيل"),
    include_inactive: bool = Query(False, description="تضمين الوكلاء غير النشطين"),
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """
    الحصول على وكيل بالمعرف.
    
    Args:
        agent_id: معرف الوكيل
        include_inactive: تضمين الوكلاء غير النشطين
        
    Returns:
        AgentResponse: الوكيل المطلوب
        
    Raises:
        HTTPException: إذا لم يتم العثور على الوكيل
    """
    logger.info(
        "api_get_agent_by_id",
        extra={
            "agent_id": agent_id,
            "include_inactive": include_inactive,
        },
    )

    try:
        agent = await service.get_by_id(
            agent_id=agent_id,
            include_inactive=include_inactive,
        )
        return agent

    except NotFoundError as e:
        logger.warning(
            "api_agent_not_found",
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
            "api_get_agent_by_id_error",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب الوكيل",
        )


# ==============================================
# GET AGENT WITH CHANNELS
# ==============================================

@router.get(
    "/{agent_id}/with-channels",
    response_model=AgentResponse,
    summary="الحصول على وكيل مع قنواته",
    description="الحصول على وكيل محدد مع جميع قنواته",
)
async def get_agent_with_channels(
    *,
    agent_id: int = Path(..., ge=1, description="معرف الوكيل"),
    include_inactive: bool = Query(False, description="تضمين الوكلاء غير النشطين"),
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """
    الحصول على وكيل مع قنواته.
    
    Args:
        agent_id: معرف الوكيل
        include_inactive: تضمين الوكلاء غير النشطين
        
    Returns:
        AgentResponse: الوكيل المطلوب مع القنوات
        
    Raises:
        HTTPException: إذا لم يتم العثور على الوكيل
    """
    logger.info(
        "api_get_agent_with_channels",
        extra={
            "agent_id": agent_id,
            "include_inactive": include_inactive,
        },
    )

    try:
        agent = await service.get_with_channels(
            agent_id=agent_id,
            include_inactive=include_inactive,
        )
        return agent

    except NotFoundError as e:
        logger.warning(
            "api_agent_not_found_with_channels",
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
            "api_get_agent_with_channels_error",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب الوكيل مع القنوات",
        )


# ==============================================
# LIST AGENTS BY RESTAURANT
# ==============================================

@router.get(
    "/restaurant/{restaurant_id}",
    response_model=AgentListResponse,
    summary="قائمة وكلاء مطعم",
    description="الحصول على قائمة الوكلاء لمطعم محدد",
)
async def list_agents_by_restaurant(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    only_active: bool = Query(True, description="جلب الوكلاء النشطين فقط"),
    service: AgentService = Depends(get_agent_service),
) -> AgentListResponse:
    """
    الحصول على قائمة وكلاء مطعم معين.
    
    Args:
        restaurant_id: معرف المطعم
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        only_active: جلب الوكلاء النشطين فقط
        
    Returns:
        AgentListResponse: قائمة الوكلاء مع الإحصائيات
    """
    logger.info(
        "api_list_agents_by_restaurant",
        extra={
            "restaurant_id": restaurant_id,
            "skip": skip,
            "limit": limit,
            "only_active": only_active,
        },
    )

    try:
        return await service.get_by_restaurant(
            restaurant_id=restaurant_id,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_list_agents_by_restaurant_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة الوكلاء",
        )


# ==============================================
# LIST AGENTS BY STATUS
# ==============================================

@router.get(
    "/status",
    response_model=AgentListResponse,
    summary="قائمة الوكلاء حسب الحالة",
    description="الحصول على قائمة الوكلاء حسب حالة النشاط",
)
async def list_agents_by_status(
    *,
    restaurant_id: Optional[int] = Query(None, description="معرف المطعم (اختياري)"),
    is_active: bool = Query(True, description="حالة الوكيل"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: AgentService = Depends(get_agent_service),
) -> AgentListResponse:
    """
    الحصول على قائمة الوكلاء حسب الحالة.
    
    Args:
        restaurant_id: معرف المطعم (اختياري)
        is_active: حالة الوكيل
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        AgentListResponse: قائمة الوكلاء مع الإحصائيات
    """
    logger.info(
        "api_list_agents_by_status",
        extra={
            "restaurant_id": restaurant_id,
            "is_active": is_active,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        return await service.get_by_status(
            restaurant_id=restaurant_id,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_list_agents_by_status_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة الوكلاء حسب الحالة",
        )


# ==============================================
# SEARCH AGENTS
# ==============================================

@router.get(
    "/search",
    response_model=AgentListResponse,
    summary="البحث عن الوكلاء",
    description="البحث عن الوكلاء باستخدام كلمات مفتاحية",
)
async def search_agents(
    *,
    query: str = Query(..., min_length=1, max_length=100, description="نص البحث"),
    restaurant_id: Optional[int] = Query(None, description="معرف المطعم (اختياري)"),
    only_active: bool = Query(True, description="جلب الوكلاء النشطين فقط"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: AgentService = Depends(get_agent_service),
) -> AgentListResponse:
    """
    البحث عن الوكلاء.
    
    Args:
        query: نص البحث
        restaurant_id: معرف المطعم (اختياري)
        only_active: جلب الوكلاء النشطين فقط
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        AgentListResponse: قائمة الوكلاء مع الإحصائيات
    """
    logger.info(
        "api_search_agents",
        extra={
            "query": query,
            "restaurant_id": restaurant_id,
            "only_active": only_active,
        },
    )

    try:
        return await service.search(
            query=query,
            restaurant_id=restaurant_id,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_search_agents_error",
            extra={
                "query": query,
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء البحث عن الوكلاء",
        )


# ==============================================
# UPDATE AGENT
# ==============================================

@router.patch(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="تحديث وكيل",
    description="تحديث بيانات وكيل موجود",
)
async def update_agent(
    *,
    agent_id: int = Path(..., ge=1, description="معرف الوكيل"),
    data: AgentUpdate,
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """
    تحديث وكيل موجود.
    
    Args:
        agent_id: معرف الوكيل
        data: بيانات التحديث
        
    Returns:
        AgentResponse: الوكيل المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على الوكيل أو حدث تعارض
    """
    logger.info(
        "api_update_agent",
        extra={
            "agent_id": agent_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        agent = await service.update(
            agent_id=agent_id,
            update_data=data,
        )
        return agent

    except NotFoundError as e:
        logger.warning(
            "api_agent_not_found_for_update",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_update_agent_conflict",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_agent_validation_error",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_agent_error",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث الوكيل",
        )


# ==============================================
# UPDATE AGENT CONFIG
# ==============================================

@router.patch(
    "/{agent_id}/config",
    response_model=AgentResponse,
    summary="تحديث إعدادات الوكيل",
    description="تحديث إعدادات الوكيل أو إعدادات الذكاء الاصطناعي",
)
async def update_agent_config(
    *,
    agent_id: int = Path(..., ge=1, description="معرف الوكيل"),
    data: AgentConfigUpdate,
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """
    تحديث إعدادات الوكيل.
    
    Args:
        agent_id: معرف الوكيل
        data: بيانات الإعدادات
        
    Returns:
        AgentResponse: الوكيل المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على الوكيل
    """
    logger.info(
        "api_update_agent_config",
        extra={
            "agent_id": agent_id,
        },
    )

    try:
        agent = await service.update_config(
            agent_id=agent_id,
            config_data=data,
        )
        return agent

    except NotFoundError as e:
        logger.warning(
            "api_agent_not_found_for_config_update",
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
            "api_update_agent_config_error",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث إعدادات الوكيل",
        )


# ==============================================
# TOGGLE AGENT STATUS
# ==============================================

@router.patch(
    "/{agent_id}/toggle-status",
    response_model=AgentResponse,
    summary="تبديل حالة الوكيل",
    description="تفعيل أو إلغاء تنشيط وكيل",
)
async def toggle_agent_status(
    *,
    agent_id: int = Path(..., ge=1, description="معرف الوكيل"),
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """
    تبديل حالة الوكيل (نشط/غير نشط).
    
    Args:
        agent_id: معرف الوكيل
        
    Returns:
        AgentResponse: الوكيل المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على الوكيل
    """
    logger.info(
        "api_toggle_agent_status",
        extra={"agent_id": agent_id},
    )

    try:
        agent = await service.toggle_active(agent_id=agent_id)
        return agent

    except NotFoundError as e:
        logger.warning(
            "api_agent_not_found_for_status_toggle",
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
            "api_toggle_agent_status_error",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تبديل حالة الوكيل",
        )


# ==============================================
# BULK TOGGLE AGENTS STATUS
# ==============================================

@router.patch(
    "/bulk/toggle-status",
    response_model=dict,
    summary="تبديل حالة مجموعة وكلاء",
    description="تفعيل أو إلغاء تنشيط مجموعة من الوكلاء دفعة واحدة",
)
async def bulk_toggle_agents_status(
    *,
    agent_ids: list[int] = Query(..., description="قائمة معرفات الوكلاء"),
    is_active: bool = Query(..., description="الحالة الجديدة"),
    service: AgentService = Depends(get_agent_service),
) -> dict:
    """
    تبديل حالة مجموعة من الوكلاء.
    
    Args:
        agent_ids: قائمة معرفات الوكلاء
        is_active: الحالة الجديدة
        
    Returns:
        dict: عدد الوكلاء المحدثين
    """
    logger.info(
        "api_bulk_toggle_agents_status",
        extra={
            "agent_ids": agent_ids,
            "is_active": is_active,
        },
    )

    try:
        count = await service.bulk_toggle_active(
            agent_ids=agent_ids,
            is_active=is_active,
        )
        return {
            "updated_count": count,
            "is_active": is_active,
        }

    except Exception as e:
        logger.exception(
            "api_bulk_toggle_agents_status_error",
            extra={
                "agent_ids": agent_ids,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تبديل حالة الوكلاء",
        )


# ==============================================
# DELETE AGENT
# ==============================================

@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف وكيل",
    description="حذف وكيل موجود",
)
async def delete_agent(
    *,
    agent_id: int = Path(..., ge=1, description="معرف الوكيل"),
    permanent: bool = Query(False, description="حذف نهائي"),
    service: AgentService = Depends(get_agent_service),
) -> None:
    """
    حذف وكيل.
    
    Args:
        agent_id: معرف الوكيل
        permanent: حذف نهائي
        
    Raises:
        HTTPException: إذا لم يتم العثور على الوكيل
    """
    logger.info(
        "api_delete_agent",
        extra={
            "agent_id": agent_id,
            "permanent": permanent,
        },
    )

    try:
        await service.delete(
            agent_id=agent_id,
            permanent=permanent,
        )

    except NotFoundError as e:
        logger.warning(
            "api_agent_not_found_for_delete",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_delete_agent_validation_error",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_agent_error",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف الوكيل",
        )

    logger.info(
        "api_agent_deleted_successfully",
        extra={
            "agent_id": agent_id,
            "permanent": permanent,
        },
    )


# ==============================================
# GET AGENT STATISTICS
# ==============================================

@router.get(
    "/statistics/{restaurant_id}",
    response_model=AgentStatistics,
    summary="إحصائيات الوكلاء",
    description="الحصول على إحصائيات الوكلاء لمطعم محدد",
)
async def get_agent_statistics(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: AgentService = Depends(get_agent_service),
) -> AgentStatistics:
    """
    الحصول على إحصائيات الوكلاء لمطعم معين.
    
    Args:
        restaurant_id: معرف المطعم
        
    Returns:
        AgentStatistics: إحصائيات الوكلاء
    """
    logger.info(
        "api_get_agent_statistics",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        stats = await service.get_statistics(restaurant_id=restaurant_id)
        return AgentStatistics(
            total_agents=stats["total_agents"],
            active_agents=stats["active_agents"],
            inactive_agents=stats["inactive_agents"],
            language_distribution=stats["language_distribution"],
            tone_distribution=stats["tone_distribution"],
        )

    except Exception as e:
        logger.exception(
            "api_get_agent_statistics_error",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب إحصائيات الوكلاء",
        )