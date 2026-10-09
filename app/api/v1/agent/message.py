# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 💬 MESSAGES API
# نقاط نهاية API للرسائل (CRUD)
# تدير عمليات إنشاء واستعراض وتحديث وحذف الرسائل
# ==============================================

"""MoulAI operational module for message.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import Optional, Any, Dict, List

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
    NotFoundError,
    ValidationError,
)
from app.schemas.agent import (
    MessageCreate,
    MessageResponse,
    MessageUpdate,
    MessageListResponse,
)
from app.services.business.agent.message_service import MessageService

# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/messages",
    tags=["💬 Messages"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================


async def get_message_service(
    session: AsyncSession = Depends(get_db),
) -> MessageService:
    """
    الحصول على خدمة الرسائل.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        MessageService: مثيل من MessageService
    """
    return MessageService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# CREATE MESSAGE
# ==============================================


@router.post(
    "/",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء رسالة جديدة",
    description="إنشاء رسالة جديدة في النظام",
)
async def create_message(
    *,
    data: MessageCreate,
    service: MessageService = Depends(get_message_service),
) -> MessageResponse:
    """
    إنشاء رسالة جديدة.

    Args:
        data: بيانات الرسالة

    Returns:
        MessageResponse: الرسالة المنشأة

    Raises:
        HTTPException: إذا لم يتم العثور على المحادثة
    """
    logger.info(
        "api_create_message",
        extra={
            "conversation_id": data.conversation_id,
            "role": data.role,
        },
    )

    try:
        message = await service.create(message_data=data)
        return message

    except NotFoundError as e:
        logger.warning(
            "api_create_message_not_found",
            extra={
                "conversation_id": data.conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_message_validation_error",
            extra={
                "conversation_id": data.conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_message_error",
            extra={
                "conversation_id": data.conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء الرسالة",
        )


# ==============================================
# CREATE USER MESSAGE
# ==============================================


@router.post(
    "/user",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء رسالة مستخدم",
    description="إنشاء رسالة مستخدم جديدة في النظام",
)
async def create_user_message(
    *,
    conversation_id: int = Query(..., ge=1, description="معرف المحادثة"),
    content: str = Query(..., description="محتوى الرسالة"),
    content_type: str = Query("text", description="نوع المحتوى"),
    intent: Optional[str] = Query(None, description="نية الرسالة"),
    confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="درجة الثقة"),
    service: MessageService = Depends(get_message_service),
) -> MessageResponse:
    """
    إنشاء رسالة مستخدم.

    Args:
        conversation_id: معرف المحادثة
        content: محتوى الرسالة
        content_type: نوع المحتوى
        intent: نية الرسالة
        confidence: درجة الثقة

    Returns:
        MessageResponse: الرسالة المنشأة
    """
    logger.info(
        "api_create_user_message",
        extra={
            "conversation_id": conversation_id,
        },
    )

    try:
        message = await service.create_user_message(
            conversation_id=conversation_id,
            content=content,
            content_type=content_type,
            intent=intent,
            confidence=confidence,
        )
        return message

    except NotFoundError as e:
        logger.warning(
            "api_create_user_message_not_found",
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
            "api_create_user_message_validation_error",
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
            "api_create_user_message_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء رسالة المستخدم",
        )


# ==============================================
# CREATE ASSISTANT MESSAGE
# ==============================================


@router.post(
    "/assistant",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء رسالة مساعد",
    description="إنشاء رسالة مساعد جديدة في النظام",
)
async def create_assistant_message(
    *,
    conversation_id: int = Query(..., ge=1, description="معرف المحادثة"),
    content: str = Query(..., description="محتوى الرسالة"),
    content_type: str = Query("text", description="نوع المحتوى"),
    intent: Optional[str] = Query(None, description="نية الرسالة"),
    confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="درجة الثقة"),
    service: MessageService = Depends(get_message_service),
) -> MessageResponse:
    """
    إنشاء رسالة مساعد.

    Args:
        conversation_id: معرف المحادثة
        content: محتوى الرسالة
        content_type: نوع المحتوى
        intent: نية الرسالة
        confidence: درجة الثقة

    Returns:
        MessageResponse: الرسالة المنشأة
    """
    logger.info(
        "api_create_assistant_message",
        extra={
            "conversation_id": conversation_id,
        },
    )

    try:
        message = await service.create_assistant_message(
            conversation_id=conversation_id,
            content=content,
            content_type=content_type,
            intent=intent,
            confidence=confidence,
        )
        return message

    except NotFoundError as e:
        logger.warning(
            "api_create_assistant_message_not_found",
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
            "api_create_assistant_message_validation_error",
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
            "api_create_assistant_message_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء رسالة المساعد",
        )


# ==============================================
# CREATE SYSTEM MESSAGE
# ==============================================


@router.post(
    "/system",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء رسالة نظام",
    description="إنشاء رسالة نظام جديدة في النظام",
)
async def create_system_message(
    *,
    conversation_id: int = Query(..., ge=1, description="معرف المحادثة"),
    content: str = Query(..., description="محتوى الرسالة"),
    intent: Optional[str] = Query(None, description="نية الرسالة"),
    confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="درجة الثقة"),
    service: MessageService = Depends(get_message_service),
) -> MessageResponse:
    """
    إنشاء رسالة نظام.

    Args:
        conversation_id: معرف المحادثة
        content: محتوى الرسالة
        intent: نية الرسالة
        confidence: درجة الثقة

    Returns:
        MessageResponse: الرسالة المنشأة
    """
    logger.info(
        "api_create_system_message",
        extra={
            "conversation_id": conversation_id,
        },
    )

    try:
        message = await service.create_system_message(
            conversation_id=conversation_id,
            content=content,
            intent=intent,
            confidence=confidence,
        )
        return message

    except NotFoundError as e:
        logger.warning(
            "api_create_system_message_not_found",
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
            "api_create_system_message_validation_error",
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
            "api_create_system_message_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء رسالة النظام",
        )


# ==============================================
# BULK CREATE MESSAGES
# ==============================================


@router.post(
    "/bulk",
    response_model=List[MessageResponse],
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء مجموعة رسائل",
    description="إنشاء مجموعة من الرسائل دفعة واحدة",
)
async def bulk_create_messages(
    *,
    conversation_id: int = Query(..., ge=1, description="معرف المحادثة"),
    messages: List[Dict[str, Any]],
    service: MessageService = Depends(get_message_service),
) -> List[MessageResponse]:
    """
    إنشاء مجموعة من الرسائل دفعة واحدة.

    Args:
        conversation_id: معرف المحادثة
        messages: قائمة بيانات الرسائل

    Returns:
        List[MessageResponse]: قائمة الرسائل المنشأة
    """
    logger.info(
        "api_bulk_create_messages",
        extra={
            "conversation_id": conversation_id,
            "count": len(messages),
        },
    )

    try:
        created_messages = await service.bulk_create_messages(
            conversation_id=conversation_id,
            messages=messages,
        )
        return created_messages

    except NotFoundError as e:
        logger.warning(
            "api_bulk_create_messages_not_found",
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
            "api_bulk_create_messages_validation_error",
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
            "api_bulk_create_messages_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء مجموعة الرسائل",
        )


# ==============================================
# GET MESSAGE BY ID
# ==============================================


@router.get(
    "/{message_id}",
    response_model=MessageResponse,
    summary="الحصول على رسالة بالمعرف",
    description="الحصول على رسالة محددة بواسطة معرفها",
)
async def get_message_by_id(
    *,
    message_id: int = Path(..., ge=1, description="معرف الرسالة"),
    service: MessageService = Depends(get_message_service),
) -> MessageResponse:
    """
    الحصول على رسالة بالمعرف.

    Args:
        message_id: معرف الرسالة

    Returns:
        MessageResponse: الرسالة المطلوبة

    Raises:
        HTTPException: إذا لم يتم العثور على الرسالة
    """
    logger.info(
        "api_get_message_by_id",
        extra={"message_id": message_id},
    )

    try:
        message = await service.get_by_id(message_id=message_id)
        return message

    except NotFoundError as e:
        logger.warning(
            "api_message_not_found",
            extra={
                "message_id": message_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_message_by_id_error",
            extra={
                "message_id": message_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب الرسالة",
        )


# ==============================================
# LIST MESSAGES BY CONVERSATION
# ==============================================


@router.get(
    "/conversation/{conversation_id}",
    response_model=MessageListResponse,
    summary="قائمة رسائل محادثة",
    description="الحصول على قائمة الرسائل لمحادثة محددة",
)
async def list_messages_by_conversation(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: MessageService = Depends(get_message_service),
) -> MessageListResponse:
    """
    الحصول على قائمة رسائل محادثة معينة.

    Args:
        conversation_id: معرف المحادثة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        MessageListResponse: قائمة الرسائل مع الإحصائيات
    """
    logger.info(
        "api_list_messages_by_conversation",
        extra={
            "conversation_id": conversation_id,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        return await service.get_by_conversation(
            conversation_id=conversation_id,
            skip=skip,
            limit=limit,
        )

    except NotFoundError as e:
        logger.warning(
            "api_conversation_not_found_for_messages",
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
            "api_list_messages_by_conversation_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة الرسائل",
        )


# ==============================================
# LIST MESSAGES BY ROLE
# ==============================================


@router.get(
    "/conversation/{conversation_id}/role/{role}",
    response_model=MessageListResponse,
    summary="قائمة رسائل حسب الدور",
    description="الحصول على قائمة الرسائل حسب دور المرسل",
)
async def list_messages_by_role(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    role: str = Path(..., description="دور المرسل: user, assistant, system"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: MessageService = Depends(get_message_service),
) -> MessageListResponse:
    """
    الحصول على قائمة رسائل حسب الدور.

    Args:
        conversation_id: معرف المحادثة
        role: دور المرسل
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        MessageListResponse: قائمة الرسائل مع الإحصائيات
    """
    logger.info(
        "api_list_messages_by_role",
        extra={
            "conversation_id": conversation_id,
            "role": role,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        return await service.get_by_role(
            conversation_id=conversation_id,
            role=role,
            skip=skip,
            limit=limit,
        )

    except ValidationError as e:
        logger.warning(
            "api_list_messages_by_role_validation_error",
            extra={
                "conversation_id": conversation_id,
                "role": role,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_list_messages_by_role_error",
            extra={
                "conversation_id": conversation_id,
                "role": role,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة الرسائل حسب الدور",
        )


# ==============================================
# LIST MESSAGES BY CONTENT TYPE
# ==============================================


@router.get(
    "/conversation/{conversation_id}/type/{content_type}",
    response_model=MessageListResponse,
    summary="قائمة رسائل حسب نوع المحتوى",
    description="الحصول على قائمة الرسائل حسب نوع المحتوى",
)
async def list_messages_by_content_type(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    content_type: str = Path(
        ..., description="نوع المحتوى: text, image, audio, video, file"
    ),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: MessageService = Depends(get_message_service),
) -> MessageListResponse:
    """
    الحصول على قائمة رسائل حسب نوع المحتوى.

    Args:
        conversation_id: معرف المحادثة
        content_type: نوع المحتوى
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        MessageListResponse: قائمة الرسائل مع الإحصائيات
    """
    logger.info(
        "api_list_messages_by_content_type",
        extra={
            "conversation_id": conversation_id,
            "content_type": content_type,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        return await service.get_by_content_type(
            conversation_id=conversation_id,
            content_type=content_type,
            skip=skip,
            limit=limit,
        )

    except ValidationError as e:
        logger.warning(
            "api_list_messages_by_content_type_validation_error",
            extra={
                "conversation_id": conversation_id,
                "content_type": content_type,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_list_messages_by_content_type_error",
            extra={
                "conversation_id": conversation_id,
                "content_type": content_type,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة الرسائل حسب نوع المحتوى",
        )


# ==============================================
# GET LAST MESSAGE
# ==============================================


@router.get(
    "/conversation/{conversation_id}/last",
    response_model=Optional[MessageResponse],
    summary="الحصول على آخر رسالة",
    description="الحصول على آخر رسالة في المحادثة",
)
async def get_last_message(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    service: MessageService = Depends(get_message_service),
) -> Optional[MessageResponse]:
    """
    الحصول على آخر رسالة في المحادثة.

    Args:
        conversation_id: معرف المحادثة

    Returns:
        Optional[MessageResponse]: آخر رسالة أو None
    """
    logger.info(
        "api_get_last_message",
        extra={"conversation_id": conversation_id},
    )

    try:
        return await service.get_last_message(
            conversation_id=conversation_id,
        )

    except Exception as e:
        logger.exception(
            "api_get_last_message_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب آخر رسالة",
        )


# ==============================================
# GET FIRST MESSAGE
# ==============================================


@router.get(
    "/conversation/{conversation_id}/first",
    response_model=Optional[MessageResponse],
    summary="الحصول على أول رسالة",
    description="الحصول على أول رسالة في المحادثة",
)
async def get_first_message(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    service: MessageService = Depends(get_message_service),
) -> Optional[MessageResponse]:
    """
    الحصول على أول رسالة في المحادثة.

    Args:
        conversation_id: معرف المحادثة

    Returns:
        Optional[MessageResponse]: أول رسالة أو None
    """
    logger.info(
        "api_get_first_message",
        extra={"conversation_id": conversation_id},
    )

    try:
        return await service.get_first_message(
            conversation_id=conversation_id,
        )

    except Exception as e:
        logger.exception(
            "api_get_first_message_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب أول رسالة",
        )


# ==============================================
# SEARCH MESSAGES
# ==============================================


@router.get(
    "/search",
    response_model=MessageListResponse,
    summary="البحث عن الرسائل",
    description="البحث عن الرسائل باستخدام كلمات مفتاحية",
)
async def search_messages(
    *,
    query: str = Query(..., min_length=1, max_length=100, description="نص البحث"),
    conversation_id: Optional[int] = Query(
        None, ge=1, description="معرف المحادثة (اختياري)"
    ),
    role: Optional[str] = Query(None, description="دور المرسل (اختياري)"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: MessageService = Depends(get_message_service),
) -> MessageListResponse:
    """
    البحث عن الرسائل.

    Args:
        query: نص البحث
        conversation_id: معرف المحادثة (اختياري)
        role: دور المرسل (اختياري)
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        MessageListResponse: قائمة الرسائل مع الإحصائيات
    """
    logger.info(
        "api_search_messages",
        extra={
            "query": query,
            "conversation_id": conversation_id,
            "role": role,
        },
    )

    try:
        return await service.search(
            query=query,
            conversation_id=conversation_id,
            role=role,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_search_messages_error",
            extra={
                "query": query,
                "conversation_id": conversation_id,
                "role": role,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء البحث عن الرسائل",
        )


# ==============================================
# UPDATE MESSAGE
# ==============================================


@router.patch(
    "/{message_id}",
    response_model=MessageResponse,
    summary="تحديث رسالة",
    description="تحديث بيانات رسالة موجودة",
)
async def update_message(
    *,
    message_id: int = Path(..., ge=1, description="معرف الرسالة"),
    data: MessageUpdate,
    service: MessageService = Depends(get_message_service),
) -> MessageResponse:
    """
    تحديث رسالة موجودة.

    Args:
        message_id: معرف الرسالة
        data: بيانات التحديث

    Returns:
        MessageResponse: الرسالة المحدثة

    Raises:
        HTTPException: إذا لم يتم العثور على الرسالة
    """
    logger.info(
        "api_update_message",
        extra={
            "message_id": message_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        message = await service.update(
            message_id=message_id,
            update_data=data,
        )
        return message

    except NotFoundError as e:
        logger.warning(
            "api_message_not_found_for_update",
            extra={
                "message_id": message_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_message_validation_error",
            extra={
                "message_id": message_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_message_error",
            extra={
                "message_id": message_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث الرسالة",
        )


# ==============================================
# DELETE MESSAGE
# ==============================================


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف رسالة",
    description="حذف رسالة موجودة",
)
async def delete_message(
    *,
    message_id: int = Path(..., ge=1, description="معرف الرسالة"),
    service: MessageService = Depends(get_message_service),
) -> None:
    """
    حذف رسالة.

    Args:
        message_id: معرف الرسالة

    Raises:
        HTTPException: إذا لم يتم العثور على الرسالة
    """
    logger.info(
        "api_delete_message",
        extra={"message_id": message_id},
    )

    try:
        await service.delete(message_id=message_id)

    except NotFoundError as e:
        logger.warning(
            "api_message_not_found_for_delete",
            extra={
                "message_id": message_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_message_error",
            extra={
                "message_id": message_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف الرسالة",
        )

    logger.info(
        "api_message_deleted_successfully",
        extra={"message_id": message_id},
    )


# ==============================================
# DELETE MESSAGES BY CONVERSATION
# ==============================================


@router.delete(
    "/conversation/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف رسائل محادثة",
    description="حذف جميع رسائل محادثة محددة",
)
async def delete_messages_by_conversation(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    service: MessageService = Depends(get_message_service),
) -> None:
    """
    حذف جميع رسائل محادثة معينة.

    Args:
        conversation_id: معرف المحادثة

    Raises:
        HTTPException: إذا لم يتم العثور على المحادثة
    """
    logger.info(
        "api_delete_messages_by_conversation",
        extra={"conversation_id": conversation_id},
    )

    try:
        count = await service.delete_by_conversation(
            conversation_id=conversation_id,
        )
        logger.info(
            "api_messages_deleted_by_conversation_successfully",
            extra={
                "conversation_id": conversation_id,
                "deleted_count": count,
            },
        )

    except NotFoundError as e:
        logger.warning(
            "api_conversation_not_found_for_messages_delete",
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
            "api_delete_messages_by_conversation_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف رسائل المحادثة",
        )


# ==============================================
# DELETE OLD MESSAGES
# ==============================================


@router.delete(
    "/conversation/{conversation_id}/old",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف الرسائل القديمة",
    description="حذف الرسائل القديمة مع الاحتفاظ بعدد محدد من أحدث الرسائل",
)
async def delete_old_messages(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    keep_count: int = Query(50, ge=1, description="عدد الرسائل التي سيتم الاحتفاظ بها"),
    service: MessageService = Depends(get_message_service),
) -> None:
    """
    حذف الرسائل القديمة مع الاحتفاظ بعدد محدد من أحدث الرسائل.

    Args:
        conversation_id: معرف المحادثة
        keep_count: عدد الرسائل التي سيتم الاحتفاظ بها

    Raises:
        HTTPException: إذا لم يتم العثور على المحادثة
    """
    logger.info(
        "api_delete_old_messages",
        extra={
            "conversation_id": conversation_id,
            "keep_count": keep_count,
        },
    )

    try:
        count = await service.delete_old_messages(
            conversation_id=conversation_id,
            keep_count=keep_count,
        )
        logger.info(
            "api_old_messages_deleted_successfully",
            extra={
                "conversation_id": conversation_id,
                "deleted_count": count,
                "kept_count": keep_count,
            },
        )

    except NotFoundError as e:
        logger.warning(
            "api_conversation_not_found_for_old_messages_delete",
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
            "api_delete_old_messages_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف الرسائل القديمة",
        )


# ==============================================
# GET MESSAGE STATISTICS
# ==============================================


@router.get(
    "/statistics/{conversation_id}",
    response_model=Dict[str, Any],
    summary="إحصائيات الرسائل",
    description="الحصول على إحصائيات الرسائل لمحادثة محددة",
)
async def get_message_statistics(
    *,
    conversation_id: int = Path(..., ge=1, description="معرف المحادثة"),
    service: MessageService = Depends(get_message_service),
) -> Dict[str, Any]:
    """
    الحصول على إحصائيات الرسائل لمحادثة معينة.

    Args:
        conversation_id: معرف المحادثة

    Returns:
        Dict[str, Any]: إحصائيات الرسائل
    """
    logger.info(
        "api_get_message_statistics",
        extra={"conversation_id": conversation_id},
    )

    try:
        return await service.get_statistics(
            conversation_id=conversation_id,
        )

    except NotFoundError as e:
        logger.warning(
            "api_conversation_not_found_for_message_statistics",
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
            "api_get_message_statistics_error",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب إحصائيات الرسائل",
        )
