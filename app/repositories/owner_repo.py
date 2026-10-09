# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

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
from app.models.owner import Owner
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

OwnerData = Dict[str, Any]
OwnerUpdateData = Dict[str, Any]
OwnerList = List[Owner]

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
    ) -> Optional[Owner]:
        """
        الحصول على مالك بواسطة chat_id.

        Args:
            chat_id: معرف المستخدم في تيليجرام

        Returns:
            كائن Owner أو None
        """
        try:
            result = await self.session.execute(
                select(self.model).where(self.model.chat_id == chat_id),
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
                select(self.model)
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
                select(self.model)
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
    ) -> Optional[Any]:
        """
        الحصول على تاريخ إنشاء المالك.

        Args:
            owner_id: معرف المالك

        Returns:
            تاريخ الإنشاء أو None
        """
        try:
            owner = await self.get_by_id(owner_id=owner_id)

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
    ) -> Optional[Owner]:
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
            owner_id=owner_id,
            data={"registration_status": status},
        )

    # ==============================================
    # MARK TRIAL USED
    # ==============================================

    async def mark_trial_used(
        self,
        *,
        owner_id: int,
    ) -> Optional[Owner]:
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
            owner_id=owner_id,
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
            owner = await self.get_by_id(owner_id=owner_id)

            if not owner:
                return False

            return owner.trial_used

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
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE OWNER (COMPATIBILITY)
# ==============================================


async def create_owner(
    *,
    chat_id: int,
    full_name: str,
    phone: str,
    email: str,
    session: AsyncSession,
) -> int:
    """
    إنشاء مالك جديد (دالة متوافقة مع الإصدار القديم).

    Args:
        chat_id: معرف المستخدم في تيليجرام
        full_name: الاسم الكامل
        phone: رقم الهاتف
        email: البريد الإلكتروني
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف المالك
    """
    repo = OwnerRepository(session=session)

    data: OwnerData = {
        "chat_id": chat_id,
        "full_name": full_name,
        "phone": phone,
        "email": email,
        "registration_status": "pending",
        "trial_used": False,
    }

    owner = await repo.create(data=data)

    logger.info(
        "owner_created",
        extra={
            "owner_id": owner.id,
            "chat_id": chat_id,
        },
    )

    return owner.id


# ==============================================
# GET OWNER BY ID (COMPATIBILITY)
# ==============================================


async def get_owner_by_id(
    *,
    owner_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على مالك بالمعرف (دالة متوافقة مع الإصدار القديم).

    Args:
        owner_id: معرف المالك
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات المالك أو None
    """
    repo = OwnerRepository(session=session)

    owner = await repo.get_by_id(owner_id=owner_id)

    if not owner:
        logger.warning(
            "owner_not_found_by_id",
            extra={"owner_id": owner_id},
        )
        return None

    return {
        "id": owner.id,
        "chat_id": owner.chat_id,
        "full_name": owner.full_name,
        "phone": owner.phone,
        "email": owner.email,
        "registration_status": owner.registration_status,
        "trial_used": owner.trial_used,
        "created_at": owner.created_at,
    }


# ==============================================
# GET OWNER BY CHAT ID (COMPATIBILITY)
# ==============================================


async def get_owner_by_chat_id(
    *,
    chat_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على مالك بواسطة chat_id (دالة متوافقة مع الإصدار القديم).

    Args:
        chat_id: معرف المستخدم في تيليجرام
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات المالك أو None
    """
    repo = OwnerRepository(session=session)

    owner = await repo.get_by_chat_id(chat_id=chat_id)

    if not owner:
        return None

    return {
        "id": owner.id,
        "chat_id": owner.chat_id,
        "full_name": owner.full_name,
        "phone": owner.phone,
        "email": owner.email,
        "registration_status": owner.registration_status,
        "trial_used": owner.trial_used,
        "created_at": owner.created_at,
    }


# ==============================================
# OWNER EXISTS (COMPATIBILITY)
# ==============================================


async def owner_exists(
    *,
    chat_id: int,
    session: AsyncSession,
) -> bool:
    """
    التحقق من وجود مالك بواسطة chat_id (دالة متوافقة مع الإصدار القديم).

    Args:
        chat_id: معرف المستخدم في تيليجرام
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        True إذا كان موجوداً
    """
    repo = OwnerRepository(session=session)

    return await repo.exists_by_chat_id(chat_id=chat_id)


# ==============================================
# GET OWNER CREATED AT (COMPATIBILITY)
# ==============================================


async def get_owner_created_at(
    *,
    owner_id: int,
    session: AsyncSession,
) -> Optional[Any]:
    """
    الحصول على تاريخ إنشاء المالك (دالة متوافقة مع الإصدار القديم).

    Args:
        owner_id: معرف المالك
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        تاريخ الإنشاء أو None
    """
    repo = OwnerRepository(session=session)

    return await repo.get_created_at(owner_id=owner_id)


# ==============================================
# UPDATE REGISTRATION STATUS (COMPATIBILITY)
# ==============================================


async def update_registration_status(
    *,
    owner_id: int,
    status: str,
    session: AsyncSession,
) -> None:
    """
    تحديث حالة تسجيل المالك (دالة متوافقة مع الإصدار القديم).

    Args:
        owner_id: معرف المالك
        status: الحالة الجديدة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = OwnerRepository(session=session)

    await repo.update_status(
        owner_id=owner_id,
        status=status,
    )

    logger.info(
        "owner_registration_status_updated",
        extra={
            "owner_id": owner_id,
            "status": status,
        },
    )


# ==============================================
# MARK TRIAL USED (COMPATIBILITY)
# ==============================================


async def mark_trial_used(
    *,
    owner_id: int,
    session: AsyncSession,
) -> None:
    """
    تعيين trial_used = True (دالة متوافقة مع الإصدار القديم).

    Args:
        owner_id: معرف المالك
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = OwnerRepository(session=session)

    await repo.mark_trial_used(owner_id=owner_id)

    logger.info(
        "owner_trial_marked_used",
        extra={"owner_id": owner_id},
    )


# ==============================================
# HAS USED TRIAL (COMPATIBILITY)
# ==============================================


async def has_used_trial(
    *,
    owner_id: int,
    session: AsyncSession,
) -> bool:
    """
    التحقق من استخدام الفترة التجريبية (دالة متوافقة مع الإصدار القديم).

    Args:
        owner_id: معرف المالك
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        True إذا استخدم الفترة التجريبية
    """
    repo = OwnerRepository(session=session)

    return await repo.has_used_trial(owner_id=owner_id)


# ==============================================
# GET ALL OWNERS (COMPATIBILITY)
# ==============================================


async def get_all_owners(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على جميع المالكين (دالة متوافقة مع الإصدار القديم).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        قائمة المالكين
    """
    repo = OwnerRepository(session=session)

    owners = await repo.get_all(
        skip=skip,
        limit=limit,
        order_by="created_at",
        descending=True,
    )

    result = []

    for owner in owners:
        result.append(
            {
                "id": owner.id,
                "chat_id": owner.chat_id,
                "full_name": owner.full_name,
                "phone": owner.phone,
                "email": owner.email,
                "registration_status": owner.registration_status,
                "trial_used": owner.trial_used,
                "created_at": owner.created_at,
            }
        )

    logger.info(
        "owners_fetched",
        extra={"count": len(result)},
    )

    return result
