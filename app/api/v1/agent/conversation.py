# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 💬 CONVERSATIONS API
# نقاط نهاية API للمحادثات (CRUD)
# تدير عمليات إنشاء واستعراض وتحديث وحذف المحادثات
# ==============================================

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
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    ConversationListResponse,
    ConversationStatistics,
)
from app.services.business.agent.conversation_service import ConversationService


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/conversations",
    tags=["💬 Conversations"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================

async def get_conversation_service(
    session: AsyncSession = Depends(get_db),
) -> ConversationService:
    """
    الحصول على خدمة المحادثات.
    
    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        ConversationService: مثيل من ConversationService
    """
    return ConversationService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# CREATE CONVERSATION
# ==============================================

@router.post(
    "/",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء محادثة جديدة",
    description="إنشاء محادثة جديدة في النظام",
)
async def create_conversation(
    *,
    data: ConversationCreate,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    """
    إنشاء محادثة جديدة.
    
    Args:
        data: بيانات المحادثة
        
    Returns:
        ConversationResponse: المحادثة المنشأة
        
    Raises:
        HTTPException: إذا لم يتم العثور على الوكيل أو القناة
    """
    logger.info(
        "api_create_conversation",
        extra={
            "agent_id": data.agent_id,
            "user_id": data.user_id,
        },
    )

    try:
        conversation = await service.create(conversation_data=data)
        return conversation

    except NotFoundError as e:
        logger.warning(
            "api_create_conversation_not_found",
            extra={
                "agent_id": data.agent_id,
                "user_id": data.user_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_conversation_validation_error",
            extra={
                "agent_id": data.agent_id,
                "user_id": data.user_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_conversation_error",
            extra={
                "agent_id": data.agent_id,
                "user_id": data.user_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء المحادثة",
        )


# ==============================================
# GET CONVERSATION BY ID
# ==============================================

@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="الحصول على محادثة بالمعرف",
    description="الحصول على محادثة محددة بواسطة معرفها",
)
async def get_conversation_by_id(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    include_inactive: bool = Query(False, description="تضمين المحادثات غير النشطة"),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    """
    الحصول على محادثة بالمعرف.
    
    Args:
        conversation_id: معرف المحادثة
        include_inactive: تضمين المحادثات غير النشطة
        
    Returns:
        ConversationResponse: المحادثة المطلوبة
        
    Raises:
        HTTPException: إذا لم يتم العثور على المحادثة
    """
    logger.info(
        "api_get_conversation_by_id",
        extra={
            "conversation_id": conversation_id,
            "include_inactive": include_inactive,
        },
    )

    try:
        conversation = await service.get_by_id(
            conversation_id=conversation_id,
            include_inactive=include_inactive,
        )
        return conversation

    except NotFoundError as e:
        logger.warning(
            "api_conversation_not_found",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_conversation_by_id_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب المحادثة",
        )


# ==============================================
# GET CONVERSATION WITH MESSAGES
# ==============================================

@router.get(
    "/{conversation_id}/with-messages",
    response_model=ConversationResponse,
    summary="الحصول على محادثة مع رسائلها",
    description="الحصول على محادثة محددة مع جميع رسائلها",
)
async def get_conversation_with_messages(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    include_inactive: bool = Query(False, description="تضمين المحادثات غير النشطة"),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    """
    الحصول على محادثة مع رسائلها.
    
    Args:
        conversation_id: معرف المحادثة
        include_inactive: تضمين المحادثات غير النشطة
        
    Returns:
        ConversationResponse: المحادثة المطلوبة مع الرسائل
        
    Raises:
        HTTPException: إذا لم يتم العثور على المحادثة
    """
    logger.info(
        "api_get_conversation_with_messages",
        extra={
            "conversation_id": conversation_id,
            "include_inactive": include_inactive,
        },
    )

    try:
        conversation = await service.get_with_messages(
            conversation_id=conversation_id,
            include_inactive=include_inactive,
        )
        return conversation

    except NotFoundError as e:
        logger.warning(
            "api_conversation_not_found_with_messages",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_conversation_with_messages_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب المحادثة مع الرسائل",
        )


# ==============================================
# GET CONVERSATION BY USER
# ==============================================

@router.get(
    "/user",
    response_model=Optional[ConversationResponse],
    summary="الحصول على محادثة حسب المستخدم",
    description="الحصول على محادثة محددة حسب معرف المستخدم",
)
async def get_conversation_by_user(
    *,
    agent_id: int = Query(..., ge=1, description="معرف الوكيل"),
    user_id: str = Query(..., description="معرف المستخدم"),
    only_active: bool = Query(True, description="جلب المحادثة النشطة فقط"),
    service: ConversationService = Depends(get_conversation_service),
) -> Optional[ConversationResponse]:
    """
    الحصول على محادثة حسب معرف المستخدم.
    
    Args:
        agent_id: معرف الوكيل
        user_id: معرف المستخدم
        only_active: جلب المحادثة النشطة فقط
        
    Returns:
        Optional[ConversationResponse]: المحادثة المطلوبة أو None
    """
    logger.info(
        "api_get_conversation_by_user",
        extra={
            "agent_id": agent_id,
            "user_id": user_id,
            "only_active": only_active,
        },
    )

    try:
        return await service.get_by_user(
            agent_id=agent_id,
            user_id=user_id,
            only_active=only_active,
        )

    except Exception as e:
        logger.exception(
            "api_get_conversation_by_user_error",
            extra={
                "agent_id": agent_id,
                "user_id": user_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب المحادثة حسب المستخدم",
        )


# ==============================================
# LIST CONVERSATIONS BY AGENT
# ==============================================

@router.get(
    "/agent/{agent_id}",
    response_model=ConversationListResponse,
    summary="قائمة محادثات وكيل",
    description="الحصول على قائمة المحادثات لوكيل محدد",
)
async def list_conversations_by_agent(
    *,
    agent_id: int = Path(..., ge=1, description="معرف الوكيل"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    only_active: bool = Query(True, description="جلب المحادثات النشطة فقط"),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationListResponse:
    """
    الحصول على قائمة محادثات وكيل معين.
    
    Args:
        agent_id: معرف الوكيل
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        only_active: جلب المحادثات النشطة فقط
        
    Returns:
        ConversationListResponse: قائمة المحادثات مع الإحصائيات
    """
    logger.info(
        "api_list_conversations_by_agent",
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
            "api_agent_not_found_for_conversations",
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
            "api_list_conversations_by_agent_error",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة المحادثات",
        )


# ==============================================
# LIST CONVERSATIONS BY STATUS
# ==============================================

@router.get(
    "/status/{status}",
    response_model=ConversationListResponse,
    summary="قائمة المحادثات حسب الحالة",
    description="الحصول على قائمة المحادثات حسب حالتها",
)
async def list_conversations_by_status(
    *,
    agent_id: int = Query(..., ge=1, description="معرف الوكيل"),
    status: str = Path(..., description="حالة المحادثة: active, closed, suspended"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationListResponse:
    """
    الحصول على قائمة المحادثات حسب الحالة.
    
    Args:
        agent_id: معرف الوكيل
        status: حالة المحادثة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        ConversationListResponse: قائمة المحادثات مع الإحصائيات
    """
    logger.info(
        "api_list_conversations_by_status",
        extra={
            "agent_id": agent_id,
            "status": status,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        return await service.get_by_status(
            agent_id=agent_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    except ValidationError as e:
        logger.warning(
            "api_list_conversations_by_status_validation_error",
            extra={
                "agent_id": agent_id,
                "status": status,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_list_conversations_by_status_error",
            extra={
                "agent_id": agent_id,
                "status": status,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة المحادثات حسب الحالة",
        )


# ==============================================
# SEARCH CONVERSATIONS
# ==============================================

@router.get(
    "/search",
    response_model=ConversationListResponse,
    summary="البحث عن المحادثات",
    description="البحث عن المحادثات باستخدام كلمات مفتاحية",
)
async def search_conversations(
    *,
    query: str = Query(..., min_length=1, max_length=100, description="نص البحث"),
    agent_id: Optional[int] = Query(None, ge=1, description="معرف الوكيل (اختياري)"),
    only_active: bool = Query(True, description="جلب المحادثات النشطة فقط"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationListResponse:
    """
    البحث عن المحادثات.
    
    Args:
        query: نص البحث
        agent_id: معرف الوكيل (اختياري)
        only_active: جلب المحادثات النشطة فقط
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        ConversationListResponse: قائمة المحادثات مع الإحصائيات
    """
    logger.info(
        "api_search_conversations",
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
            "api_search_conversations_error",
            extra={
                "query": query,
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء البحث عن المحادثات",
        )


# ==============================================
# UPDATE CONVERSATION
# ==============================================

@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="تحديث محادثة",
    description="تحديث بيانات محادثة موجودة",
)
async def update_conversation(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    data: ConversationUpdate,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    """
    تحديث محادثة موجودة.
    
    Args:
        conversation_id: معرف المحادثة
        data: بيانات التحديث
        
    Returns:
        ConversationResponse: المحادثة المحدثة
        
    Raises:
        HTTPException: إذا لم يتم العثور على المحادثة
    """
    logger.info(
        "api_update_conversation",
        extra={
            "conversation_id": conversation_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        conversation = await service.update(
            conversation_id=conversation_id,
            update_data=data,
        )
        return conversation

    except NotFoundError as e:
        logger.warning(
            "api_conversation_not_found_for_update",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_conversation_validation_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_conversation_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث المحادثة",
        )


# ==============================================
# UPDATE CONVERSATION CONTEXT
# ==============================================

@router.patch(
    "/{conversation_id}/context",
    response_model=ConversationResponse,
    summary="تحديث سياق المحادثة",
    description="تحديث سياق محادثة موجودة",
)
async def update_conversation_context(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    context: Dict[str, Any],
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    """
    تحديث سياق المحادثة.
    
    Args:
        conversation_id: معرف المحادثة
        context: السياق الجديد
        
    Returns:
        ConversationResponse: المحادثة المحدثة
        
    Raises:
        HTTPException: إذا لم يتم العثور على المحادثة
    """
    logger.info(
        "api_update_conversation_context",
        extra={
            "conversation_id": conversation_id,
        },
    )

    try:
        conversation = await service.update_context(
            conversation_id=conversation_id,
            context=context,
        )
        return conversation

    except NotFoundError as e:
        logger.warning(
            "api_conversation_not_found_for_context_update",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_conversation_context_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث سياق المحادثة",
        )


# ==============================================
# UPDATE CONVERSATION STATUS
# ==============================================

@router.patch(
    "/{conversation_id}/status",
    response_model=ConversationResponse,
    summary="تحديث حالة المحادثة",
    description="تحديث حالة محادثة موجودة",
)
async def update_conversation_status(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    status: str = Query(..., description="الحالة الجديدة: active, closed, suspended"),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    """
    تحديث حالة المحادثة.
    
    Args:
        conversation_id: معرف المحادثة
        status: الحالة الجديدة
        
    Returns:
        ConversationResponse: المحادثة المحدثة
        
    Raises:
        HTTPException: إذا لم يتم العثور على المحادثة
    """
    logger.info(
        "api_update_conversation_status",
        extra={
            "conversation_id": conversation_id,
            "status": status,
        },
    )

    try:
        conversation = await service.update_status(
            conversation_id=conversation_id,
            status=status,
        )
        return conversation

    except NotFoundError as e:
        logger.warning(
            "api_conversation_not_found_for_status_update",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_conversation_status_validation_error",
            extra={
                "conversation_id": conversation_id,
                "status": status,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_conversation_status_error",
            extra={
                "conversation_id": conversation_id,
                "status": status,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث حالة المحادثة",
        )


# ==============================================
# TOGGLE CONVERSATION STATUS
# ==============================================

@router.patch(
    "/{conversation_id}/toggle-status",
    response_model=ConversationResponse,
    summary="تبديل حالة المحادثة",
    description="تفعيل أو إلغاء تنشيط محادثة",
)
async def toggle_conversation_status(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    """
    تبديل حالة المحادثة (نشط/غير نشط).
    
    Args:
        conversation_id: معرف المحادثة
        
    Returns:
        ConversationResponse: المحادثة المحدثة
        
    Raises:
        HTTPException: إذا لم يتم العثور على المحادثة
    """
    logger.info(
        "api_toggle_conversation_status",
        extra={"conversation_id": conversation_id},
    )

    try:
        conversation = await service.deactivate(
            conversation_id=conversation_id,
        )
        return conversation

    except NotFoundError as e:
        logger.warning(
            "api_conversation_not_found_for_status_toggle",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_toggle_conversation_status_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تبديل حالة المحادثة",
        )


# ==============================================
# DELETE CONVERSATION
# ==============================================

@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف محادثة",
    description="حذف محادثة موجودة",
)
async def delete_conversation(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    permanent: bool = Query(False, description="حذف نهائي"),
    service: ConversationService = Depends(get_conversation_service),
) -> None:
    """
    حذف محادثة.
    
    Args:
        conversation_id: معرف المحادثة
        permanent: حذف نهائي
        
    Raises:
        HTTPException: إذا لم يتم العثور على المحادثة
    """
    logger.info(
        "api_delete_conversation",
        extra={
            "conversation_id": conversation_id,
            "permanent": permanent,
        },
    )

    try:
        await service.delete(
            conversation_id=conversation_id,
            permanent=permanent,
        )

    except NotFoundError as e:
        logger.warning(
            "api_conversation_not_found_for_delete",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_delete_conversation_validation_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_conversation_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف المحادثة",
        )

    logger.info(
        "api_conversation_deleted_successfully",
        extra={
            "conversation_id": conversation_id,
            "permanent": permanent,
        },
    )


# ==============================================
# GET CONVERSATION STATISTICS
# ==============================================

@router.get(
    "/statistics/{agent_id}",
    response_model=ConversationStatistics,
    summary="إحصائيات المحادثات",
    description="الحصول على إحصائيات المحادثات لوكيل محدد",
)
async def get_conversation_statistics(
    *,
    agent_id: int = Path(..., ge=1, description="معرف الوكيل"),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationStatistics:
    """
    الحصول على إحصائيات المحادثات لوكيل معين.
    
    Args:
        agent_id: معرف الوكيل
        
    Returns:
        ConversationStatistics: إحصائيات المحادثات
    """
    logger.info(
        "api_get_conversation_statistics",
        extra={"agent_id": agent_id},
    )

    try:
        stats = await service.get_statistics(agent_id=agent_id)
        return ConversationStatistics(
            total_conversations=stats["total_conversations"],
            active_conversations=stats["active_conversations"],
            inactive_conversations=stats["inactive_conversations"],
            status_summary=stats["status_summary"],
        )

    except NotFoundError as e:
        logger.warning(
            "api_agent_not_found_for_conversation_statistics",
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
            "api_get_conversation_statistics_error",
            extra={
                "agent_id": agent_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب إحصائيات المحادثات",
        )