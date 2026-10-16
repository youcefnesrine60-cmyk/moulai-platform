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
    TypeAlias,
)

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.registration_request import RegistrationRequest
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

RegistrationRequestData: TypeAlias = dict[str, Any]
RegistrationRequestUpdateData: TypeAlias = dict[str, Any]
RegistrationRequestList: TypeAlias = list[RegistrationRequest]

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
    ) -> RegistrationRequest | None:
        """
        الحصول على طلب تسجيل بواسطة chat_id.

        Args:
            chat_id: معرف المستخدم في تيليجرام

        Returns:
            كائن RegistrationRequest أو None
        """
        try:
            result = await self.session.execute(
                self._select()
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
                self._select()
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
                self._select()
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
                self._select()
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
                self._select()
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
    ) -> RegistrationRequest | None:
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
            id=request_id,
            data={"status": status},
        )

    # ==============================================
    # APPROVE
    # ==============================================

    async def approve(
        self,
        *,
        request_id: int,
        owner_id: int | None = None,
    ) -> RegistrationRequest | None:
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
            id=request_id,
            data=data,
        )

    # ==============================================
    # REJECT
    # ==============================================

    async def reject(
        self,
        *,
        request_id: int,
    ) -> RegistrationRequest | None:
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
            id=request_id,
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
