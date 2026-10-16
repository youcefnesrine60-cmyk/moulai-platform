# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""MoulAI operational module for owner repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ==============================================
# 👤 OWNER REPOSITORY
# عمليات قاعدة البيانات للمالكين باستخدام SQLAlchemy
# ==============================================

from datetime import datetime
from typing import (
    Any,
    TypeAlias,
)

from sqlalchemy import (
    func,
    or_,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.owner import Owner
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

OwnerData: TypeAlias = dict[str, Any]
OwnerUpdateData: TypeAlias = dict[str, Any]
OwnerList: TypeAlias = list[Owner]
OwnerStatisticsData: TypeAlias = dict[str, int]

# ==============================================
# 👤 OWNER REPOSITORY
# ==============================================


class OwnerRepository(BaseRepository[Owner, OwnerData, OwnerUpdateData]):
    """
    مستودع المالكين - يوفر عمليات خاصة بالمالكين.

    مسؤول عن:
        - عمليات CRUD الأساسية للمالكين
        - البحث والتصفية حسب chat_id والحالة
        - التحقق من وجود المالكين
        - إدارة الفترة التجريبية

    Attributes:
        model: نموذج Owner
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        *,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع المالكين.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Owner, session)

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
    ) -> Owner | None:
        """
        الحصول على مالك بواسطة chat_id.

        Args:
            chat_id: معرف المستخدم في تيليجرام

        Returns:
            كائن Owner أو None
        """
        try:
            result = await self.session.execute(
                self._select().where(self.model.chat_id == chat_id),
            )

            owner = result.scalar_one_or_none()

            if owner:
                logger.info(
                    "owner_found_by_chat_id",
                    extra={
                        "chat_id": chat_id,
                        "owner_id": owner.id,
                    },
                )
            else:
                logger.info(
                    "owner_not_found_by_chat_id",
                    extra={"chat_id": chat_id},
                )

            return owner

        except Exception as e:
            logger.exception(
                "owner_repo_get_by_chat_id_failed",
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
    ) -> OwnerList:
        """
        الحصول على المالكين حسب حالة التسجيل.

        Args:
            status: حالة التسجيل (pending, approved, rejected)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة المالكين
        """
        try:
            query = (
                self._select()
                .where(self.model.registration_status == status)
                .offset(skip)
                .limit(limit)
                .order_by(self.model.created_at.desc())
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "owner_repo_get_by_status_failed",
                extra={
                    "status": status,
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
    ) -> OwnerList:
        """
        البحث عن مالكين.

        Args:
            query: نص البحث
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة المالكين
        """
        try:
            stmt = (
                self._select()
                .where(
                    or_(
                        self.model.full_name.ilike(f"%{query}%"),
                        self.model.phone.ilike(f"%{query}%"),
                        self.model.email.ilike(f"%{query}%"),
                    ),
                )
                .offset(skip)
                .limit(limit)
                .order_by(self.model.created_at.desc())
            )

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "owner_repo_search_failed",
                extra={
                    "query": query,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # EXISTS BY CHAT ID
    # ==============================================

    async def exists_by_chat_id(
        self,
        *,
        chat_id: int,
    ) -> bool:
        """
        التحقق من وجود مالك بواسطة chat_id.

        Args:
            chat_id: معرف المستخدم في تيليجرام

        Returns:
            True إذا كان موجوداً، False إذا لم يكن
        """
        try:
            owner = await self.get_by_chat_id(chat_id=chat_id)
            exists = owner is not None

            logger.info(
                "owner_exists_checked",
                extra={
                    "chat_id": chat_id,
                    "exists": exists,
                },
            )

            return exists

        except Exception as e:
            logger.exception(
                "owner_repo_exists_by_chat_id_failed",
                extra={
                    "chat_id": chat_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET CREATED AT
    # ==============================================

    async def get_created_at(
        self,
        *,
        owner_id: int,
    ) -> datetime | None:
        """
        الحصول على تاريخ إنشاء المالك.

        Args:
            owner_id: معرف المالك

        Returns:
            تاريخ الإنشاء أو None
        """
        try:
            owner = await self.get_by_id(id=owner_id)

            if owner:
                return owner.created_at

            return None

        except Exception as e:
            logger.exception(
                "owner_repo_get_created_at_failed",
                extra={
                    "owner_id": owner_id,
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
        owner_id: int,
        status: str,
    ) -> Owner | None:
        """
        تحديث حالة تسجيل المالك.

        Args:
            owner_id: معرف المالك
            status: الحالة الجديدة (pending, approved, rejected)

        Returns:
            كائن Owner المحدث أو None
        """
        logger.info(
            "owner_repo_update_status",
            extra={
                "owner_id": owner_id,
                "status": status,
            },
        )

        return await self.update(
            id=owner_id,
            data={"registration_status": status},
        )

    # ==============================================
    # MARK TRIAL USED
    # ==============================================

    async def mark_trial_used(
        self,
        *,
        owner_id: int,
    ) -> Owner | None:
        """
        تعيين trial_used = True.

        Args:
            owner_id: معرف المالك

        Returns:
            كائن Owner المحدث أو None
        """
        logger.info(
            "owner_repo_mark_trial_used",
            extra={"owner_id": owner_id},
        )

        return await self.update(
            id=owner_id,
            data={"trial_used": True},
        )

    # ==============================================
    # HAS USED TRIAL
    # ==============================================

    async def has_used_trial(
        self,
        *,
        owner_id: int,
    ) -> bool:
        """
        التحقق من استخدام الفترة التجريبية.

        Args:
            owner_id: معرف المالك

        Returns:
            True إذا استخدم الفترة التجريبية، False إذا لم يستخدم
        """
        try:
            owner = await self.get_by_id(id=owner_id)

            if not owner:
                return False

            return bool(owner.trial_used)

        except Exception as e:
            logger.exception(
                "owner_repo_has_used_trial_failed",
                extra={
                    "owner_id": owner_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET STATISTICS
    # ==============================================

    async def get_statistics(self) -> OwnerStatisticsData:
        """Count registration and trial flags in one consistent SQL snapshot.

        ``trial_available`` counts owners whose trial flag is false or absent.
        Trial activation still requires an approved registration in the
        business service. Aggregate data is exposed only to administrators.
        """
        statement = self._select().with_only_columns(
            func.count(self.model.id).label("total"),
            func.count(self.model.id)
            .filter(self.model.registration_status == "pending")
            .label("pending"),
            func.count(self.model.id)
            .filter(self.model.registration_status == "approved")
            .label("approved"),
            func.count(self.model.id)
            .filter(self.model.registration_status == "rejected")
            .label("rejected"),
            func.count(self.model.id)
            .filter(self.model.trial_used.is_(True))
            .label("trial_used"),
            func.count(self.model.id)
            .filter(self.model.trial_used.is_not(True))
            .label("trial_available"),
        )
        result = await self.session.execute(statement)
        row = result.mappings().one()
        return {name: int(value) for name, value in row.items()}


# ==============================================
