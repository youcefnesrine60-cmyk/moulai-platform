# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / REPOSITORIES / REGISTRATION REQUEST REPO
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for registration request repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ==============================================
# 📝 REGISTRATION REQUEST REPOSITORY
# عمليات قاعدة البيانات لطلبات التسجيل باستخدام SQLAlchemy
# إنشاء طلب
#    ↓
# استلام الطلب
#    ↓
# الموافقة على الطلب
#    ↓
# رفض الطلب
#    ↓
# حذف الطلب
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.registration_request import RegistrationRequest
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

RegistrationRequestData = Dict[str, Any]
RegistrationRequestUpdateData = Dict[str, Any]
RegistrationRequestList = List[RegistrationRequest]

# ==============================================
# 📝 REGISTRATION REQUEST REPOSITORY
# ==============================================


class RegistrationRequestRepository(
    BaseRepository[
        RegistrationRequest,
        RegistrationRequestData,
        RegistrationRequestUpdateData,
    ]
):
    """
    مستودع طلبات التسجيل - يوفر عمليات خاصة بطلبات التسجيل.

    مسؤول عن:
        - عمليات CRUD الأساسية لطلبات التسجيل
        - البحث والتصفية حسب chat_id والحالة
        - الموافقة والرفض على الطلبات
        - البحث النصي

    Attributes:
        model: نموذج RegistrationRequest
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع طلبات التسجيل.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(RegistrationRequest, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY CHAT ID
    # ==============================================

    async def get_by_chat_id(
        self,
        *,
        chat_id: int,
    ) -> Optional[RegistrationRequest]:
        """
        الحصول على طلب تسجيل بواسطة chat_id.

        Args:
            chat_id: معرف المستخدم في تيليجرام

        Returns:
            كائن RegistrationRequest أو None
        """
        try:
            result = await self.session.execute(
                select(self.model)
                .where(self.model.chat_id == chat_id)
                .order_by(self.model.created_at.desc())
                .limit(1),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "registration_request_repo_get_by_chat_id_failed",
                extra={
                    "chat_id": chat_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET ALL BY CHAT ID
    # ==============================================

    async def get_all_by_chat_id(
        self,
        *,
        chat_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> RegistrationRequestList:
        """
        الحصول على جميع طلبات التسجيل لمستخدم معين.

        Args:
            chat_id: معرف المستخدم في تيليجرام
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة طلبات التسجيل
        """
        try:
            query = (
                select(self.model)
                .where(self.model.chat_id == chat_id)
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "registration_request_repo_get_all_by_chat_id_failed",
                extra={
                    "chat_id": chat_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY STATUS
    # ==============================================

    async def get_by_status(
        self,
        *,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> RegistrationRequestList:
        """
        الحصول على طلبات التسجيل حسب الحالة.

        Args:
            status: حالة الطلب (pending, approved, rejected)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة طلبات التسجيل
        """
        try:
            query = (
                select(self.model)
                .where(self.model.status == status)
                .order_by(self.model.created_at.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "registration_request_repo_get_by_status_failed",
                extra={
                    "status": status,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET PENDING
    # ==============================================

    async def get_pending(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> RegistrationRequestList:
        """
        الحصول على طلبات التسجيل المعلقة (pending).

        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة طلبات التسجيل المعلقة
        """
        return await self.get_by_status(
            status="pending",
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET BY OWNER ID
    # ==============================================

    async def get_by_owner_id(
        self,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> RegistrationRequestList:
        """
        الحصول على طلبات التسجيل حسب معرف المالك.

        Args:
            owner_id: معرف المالك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة طلبات التسجيل
        """
        try:
            query = (
                select(self.model)
                .where(self.model.owner_id == owner_id)
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "registration_request_repo_get_by_owner_id_failed",
                extra={
                    "owner_id": owner_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # SEARCH
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> RegistrationRequestList:
        """
        البحث عن طلبات التسجيل.

        Args:
            query: نص البحث
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة طلبات التسجيل
        """
        try:
            stmt = (
                select(self.model)
                .where(
                    or_(
                        self.model.full_name.ilike(f"%{query}%"),
                        self.model.restaurant_name.ilike(f"%{query}%"),
                        self.model.owner_phone.ilike(f"%{query}%"),
                        self.model.email.ilike(f"%{query}%"),
                    ),
                )
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "registration_request_repo_search_failed",
                extra={
                    "query": query,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ UPDATES
    # ==========================================

    # ==============================================
    # UPDATE STATUS
    # ==============================================

    async def update_status(
        self,
        *,
        request_id: int,
        status: str,
    ) -> Optional[RegistrationRequest]:
        """
        تحديث حالة طلب التسجيل.

        Args:
            request_id: معرف طلب التسجيل
            status: الحالة الجديدة (pending, approved, rejected)

        Returns:
            كائن RegistrationRequest المحدث أو None
        """
        logger.info(
            "registration_request_repo_update_status",
            extra={
                "request_id": request_id,
                "status": status,
            },
        )

        return await self.update(
            request_id=request_id,
            data={"status": status},
        )

    # ==============================================
    # APPROVE
    # ==============================================

    async def approve(
        self,
        *,
        request_id: int,
        owner_id: Optional[int] = None,
    ) -> Optional[RegistrationRequest]:
        """
        الموافقة على طلب التسجيل.

        Args:
            request_id: معرف طلب التسجيل
            owner_id: معرف المالك (اختياري)

        Returns:
            كائن RegistrationRequest المحدث أو None
        """
        logger.info(
            "registration_request_repo_approve",
            extra={
                "request_id": request_id,
                "owner_id": owner_id,
            },
        )

        data: RegistrationRequestUpdateData = {"status": "approved"}

        if owner_id is not None:
            data["owner_id"] = owner_id

        return await self.update(
            request_id=request_id,
            data=data,
        )

    # ==============================================
    # REJECT
    # ==============================================

    async def reject(
        self,
        *,
        request_id: int,
    ) -> Optional[RegistrationRequest]:
        """
        رفض طلب التسجيل.

        Args:
            request_id: معرف طلب التسجيل

        Returns:
            كائن RegistrationRequest المحدث أو None
        """
        logger.info(
            "registration_request_repo_reject",
            extra={"request_id": request_id},
        )

        return await self.update(
            request_id=request_id,
            data={"status": "rejected"},
        )

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY STATUS
    # ==============================================

    async def count_by_status(
        self,
        *,
        status: str,
    ) -> int:
        """
        حساب عدد طلبات التسجيل حسب الحالة.

        Args:
            status: حالة الطلب

        Returns:
            عدد الطلبات
        """
        return await self.count(filters={"status": status})

    # ==============================================
    # COUNT PENDING
    # ==============================================

    async def count_pending(
        self,
    ) -> int:
        """
        حساب عدد طلبات التسجيل المعلقة.

        Returns:
            عدد الطلبات المعلقة
        """
        return await self.count_by_status(status="pending")


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE REGISTRATION REQUEST (COMPATIBILITY)
# ==============================================


async def create_registration_request(
    *,
    chat_id: int,
    full_name: str,
    owner_phone: str,
    email: Optional[str],
    restaurant_name: str,
    restaurant_type: str,
    restaurant_phone: str,
    wilaya: str,
    lat: float,
    lng: float,
    session: AsyncSession,
) -> int:
    """
    إنشاء طلب تسجيل جديد (دالة متوافقة مع الإصدار القديم).

    Args:
        chat_id: معرف المستخدم في تيليجرام
        full_name: الاسم الكامل
        owner_phone: رقم هاتف المالك
        email: البريد الإلكتروني
        restaurant_name: اسم المطعم
        restaurant_type: نوع المطعم
        restaurant_phone: رقم هاتف المطعم
        wilaya: الولاية
        lat: خط العرض
        lng: خط الطول
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف طلب التسجيل
    """
    repo = RegistrationRequestRepository(session=session)

    data: RegistrationRequestData = {
        "chat_id": chat_id,
        "full_name": full_name,
        "owner_phone": owner_phone,
        "email": email,
        "restaurant_name": restaurant_name,
        "restaurant_type": restaurant_type,
        "restaurant_phone": restaurant_phone,
        "wilaya": wilaya,
        "lat": lat,
        "lng": lng,
        "status": "pending",
    }

    request_obj = await repo.create(data=data)

    logger.info(
        "registration_request_created",
        extra={
            "request_id": request_obj.id,
            "chat_id": chat_id,
        },
    )

    return request_obj.id


# ==============================================
# GET REGISTRATION REQUEST BY ID (COMPATIBILITY)
# ==============================================


async def get_registration_request_by_id(
    *,
    request_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على طلب تسجيل بالمعرف (دالة متوافقة مع الإصدار القديم).

    Args:
        request_id: معرف طلب التسجيل
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات الطلب أو None
    """
    repo = RegistrationRequestRepository(session=session)

    request_obj = await repo.get_by_id(request_id=request_id)

    if not request_obj:
        return None

    return {
        "id": request_obj.id,
        "chat_id": request_obj.chat_id,
        "full_name": request_obj.full_name,
        "owner_phone": request_obj.owner_phone,
        "email": request_obj.email,
        "restaurant_name": request_obj.restaurant_name,
        "restaurant_type": request_obj.restaurant_type,
        "restaurant_phone": request_obj.restaurant_phone,
        "wilaya": request_obj.wilaya,
        "lat": request_obj.lat,
        "lng": request_obj.lng,
        "status": request_obj.status,
        "owner_id": request_obj.owner_id,
        "created_at": request_obj.created_at,
    }


# ==============================================
# GET REGISTRATION REQUEST BY CHAT ID (COMPATIBILITY)
# ==============================================


async def get_registration_request_by_chat_id(
    *,
    chat_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على طلب تسجيل بواسطة chat_id (دالة متوافقة مع الإصدار القديم).

    Args:
        chat_id: معرف المستخدم في تيليجرام
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات الطلب أو None
    """
    repo = RegistrationRequestRepository(session=session)

    request_obj = await repo.get_by_chat_id(chat_id=chat_id)

    if not request_obj:
        return None

    return {
        "id": request_obj.id,
        "chat_id": request_obj.chat_id,
        "full_name": request_obj.full_name,
        "owner_phone": request_obj.owner_phone,
        "email": request_obj.email,
        "restaurant_name": request_obj.restaurant_name,
        "restaurant_type": request_obj.restaurant_type,
        "restaurant_phone": request_obj.restaurant_phone,
        "wilaya": request_obj.wilaya,
        "lat": request_obj.lat,
        "lng": request_obj.lng,
        "status": request_obj.status,
        "owner_id": request_obj.owner_id,
        "created_at": request_obj.created_at,
    }


# ==============================================
# GET PENDING REQUESTS (COMPATIBILITY)
# ==============================================


async def get_pending_requests(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على طلبات التسجيل المعلقة (دالة متوافقة مع الإصدار القديم).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        قائمة طلبات التسجيل المعلقة
    """
    repo = RegistrationRequestRepository(session=session)

    requests = await repo.get_pending(
        skip=skip,
        limit=limit,
    )

    result = []

    for req in requests:
        result.append(
            {
                "id": req.id,
                "chat_id": req.chat_id,
                "full_name": req.full_name,
                "owner_phone": req.owner_phone,
                "email": req.email,
                "restaurant_name": req.restaurant_name,
                "restaurant_type": req.restaurant_type,
                "restaurant_phone": req.restaurant_phone,
                "wilaya": req.wilaya,
                "lat": req.lat,
                "lng": req.lng,
                "status": req.status,
                "owner_id": req.owner_id,
                "created_at": req.created_at,
            }
        )

    logger.info(
        "pending_requests_fetched",
        extra={"count": len(result)},
    )

    return result


# ==============================================
# APPROVE REGISTRATION REQUEST (COMPATIBILITY)
# ==============================================


async def approve_registration_request(
    *,
    request_id: int,
    session: AsyncSession,
    owner_id: Optional[int] = None,
) -> None:
    """
    الموافقة على طلب التسجيل (دالة متوافقة مع الإصدار القديم).

    Args:
        request_id: معرف طلب التسجيل
        session: جلسة قاعدة البيانات غير المتزامنة
        owner_id: معرف المالك (اختياري)
    """
    repo = RegistrationRequestRepository(session=session)

    await repo.approve(
        request_id=request_id,
        owner_id=owner_id,
    )

    logger.info(
        "registration_request_approved",
        extra={"request_id": request_id},
    )


# ==============================================
# REJECT REGISTRATION REQUEST (COMPATIBILITY)
# ==============================================


async def reject_registration_request(
    *,
    request_id: int,
    session: AsyncSession,
) -> None:
    """
    رفض طلب التسجيل (دالة متوافقة مع الإصدار القديم).

    Args:
        request_id: معرف طلب التسجيل
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = RegistrationRequestRepository(session=session)

    await repo.reject(request_id=request_id)

    logger.info(
        "registration_request_rejected",
        extra={"request_id": request_id},
    )


# ==============================================
# DELETE REGISTRATION REQUEST (COMPATIBILITY)
# ==============================================


async def delete_registration_request(
    *,
    request_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف طلب التسجيل (دالة متوافقة مع الإصدار القديم).

    Args:
        request_id: معرف طلب التسجيل
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = RegistrationRequestRepository(session=session)

    await repo.delete(request_id=request_id)

    logger.info(
        "registration_request_deleted",
        extra={"request_id": request_id},
    )
