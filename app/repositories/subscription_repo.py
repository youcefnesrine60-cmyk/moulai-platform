# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / REPOSITORIES / SUBSCRIPTION REPO
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for subscription repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ==============================================
# 💳 SUBSCRIPTION REPOSITORY
# عمليات قاعدة البيانات للاشتراكات باستخدام SQLAlchemy
# اشتراكات المطاعم
# إنشاء الاشتراك
# تفعيله
# إلغاؤه
# انتهاءه
# قراءة الاشتراكات
# ==============================================

from datetime import datetime, timedelta
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    and_,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.subscription import Subscription
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

SubscriptionData = Dict[str, Any]
SubscriptionUpdateData = Dict[str, Any]
SubscriptionList = List[Subscription]

# ==============================================
# 💳 SUBSCRIPTION REPOSITORY
# ==============================================


class SubscriptionRepository(
    BaseRepository[
        Subscription,
        SubscriptionData,
        SubscriptionUpdateData,
    ]
):
    """
    مستودع الاشتراكات - يوفر عمليات خاصة بالاشتراكات.

    مسؤول عن:
        - عمليات CRUD الأساسية للاشتراكات
        - البحث والتصفية حسب المالك والمطعم
        - إدارة حالة الاشتراكات (active, expired, cancelled)
        - التحقق من الاشتراكات النشطة

    Attributes:
        model: نموذج Subscription
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
        تهيئة مستودع الاشتراكات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Subscription, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    async def get_by_id_for_update(
        self, *, subscription_id: int
    ) -> Optional[Subscription]:
        """Lock the subscription before activation or feature transfer."""
        result = await self.session.execute(
            self._select()
            .where(self.model.id == subscription_id)
            .with_for_update(of=self.model)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    # ==============================================
    # GET BY OWNER ID
    # ==============================================

    async def get_by_owner_id(
        self,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> SubscriptionList:
        """
        الحصول على اشتراكات مالك معين.

        Args:
            owner_id: معرف المالك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الاشتراكات
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
                "subscription_repo_get_by_owner_failed",
                extra={
                    "owner_id": owner_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY RESTAURANT ID
    # ==============================================

    async def get_by_restaurant_id(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> SubscriptionList:
        """
        الحصول على اشتراكات مطعم معين.

        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الاشتراكات
        """
        try:
            query = (
                select(self.model)
                .where(self.model.restaurant_id == restaurant_id)
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "subscription_repo_get_by_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET ACTIVE BY RESTAURANT
    # ==============================================

    async def get_active_by_restaurant(
        self,
        *,
        restaurant_id: int,
    ) -> Optional[Subscription]:
        """
        الحصول على الاشتراك النشط لمطعم معين.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            كائن Subscription أو None
        """
        try:
            query = (
                select(self.model)
                .where(
                    and_(
                        self.model.restaurant_id == restaurant_id,
                        self.model.status.in_(["active", "trial"]),
                        or_(
                            self.model.expires_at.is_(None),
                            self.model.expires_at >= datetime.now(),
                        ),
                    ),
                )
                .order_by(self.model.created_at.desc())
                .limit(1)
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "subscription_repo_get_active_by_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # HAS ACTIVE SUBSCRIPTION
    # ==============================================

    async def has_active_subscription(
        self,
        *,
        restaurant_id: int,
    ) -> bool:
        """
        التحقق من وجود اشتراك نشط لمطعم معين.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            True إذا كان هناك اشتراك نشط، False إذا لم يكن
        """
        try:
            subscription = await self.get_active_by_restaurant(
                restaurant_id=restaurant_id,
            )

            exists = subscription is not None

            logger.info(
                "active_subscription_checked",
                extra={
                    "restaurant_id": restaurant_id,
                    "exists": exists,
                },
            )

            return exists

        except Exception as e:
            logger.exception(
                "subscription_repo_has_active_failed",
                extra={
                    "restaurant_id": restaurant_id,
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
    ) -> SubscriptionList:
        """
        الحصول على اشتراكات حسب الحالة.

        Args:
            status: حالة الاشتراك (pending, trial, active, expired, cancelled)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الاشتراكات
        """
        try:
            query = (
                select(self.model)
                .where(self.model.status == status)
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "subscription_repo_get_by_status_failed",
                extra={
                    "status": status,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET EXPIRING
    # ==============================================

    async def get_expiring(
        self,
        *,
        days: int = 7,
    ) -> SubscriptionList:
        """
        الحصول على الاشتراكات التي ستنتهي خلال عدد محدد من الأيام.

        Args:
            days: عدد الأيام القادمة (افتراضي: 7)

        Returns:
            قائمة الاشتراكات المنتهية قريباً
        """
        try:
            now = datetime.now()
            future = now + timedelta(days=days)

            query = (
                select(self.model)
                .where(
                    and_(
                        self.model.status == "active",
                        self.model.expires_at.is_not(None),
                        self.model.expires_at <= future,
                        self.model.expires_at >= now,
                    ),
                )
                .order_by(self.model.expires_at.asc())
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "subscription_repo_get_expiring_failed",
                extra={
                    "days": days,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET EXPIRED
    # ==============================================

    async def get_expired(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> SubscriptionList:
        """
        الحصول على الاشتراكات المنتهية.

        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الاشتراكات المنتهية
        """
        try:
            query = (
                select(self.model)
                .where(
                    and_(
                        self.model.status.in_(["active", "trial"]),
                        self.model.expires_at.is_not(None),
                        self.model.expires_at < datetime.now(),
                    ),
                )
                .order_by(self.model.expires_at.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "subscription_repo_get_expired_failed",
                extra={"error": str(e)},
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
        subscription_id: int,
        status: str,
    ) -> Optional[Subscription]:
        """
        تحديث حالة الاشتراك.

        Args:
            subscription_id: معرف الاشتراك
            status: الحالة الجديدة (pending, trial, active, expired, cancelled)

        Returns:
            كائن Subscription المحدث أو None
        """
        logger.info(
            "subscription_repo_update_status",
            extra={
                "subscription_id": subscription_id,
                "status": status,
            },
        )

        return await self.update(
            id=subscription_id,
            data={"status": status},
        )

    # ==============================================
    # ACTIVATE
    # ==============================================

    async def activate(
        self,
        *,
        subscription_id: int,
        starts_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
    ) -> Optional[Subscription]:
        """
        تفعيل الاشتراك.

        Args:
            subscription_id: معرف الاشتراك
            starts_at: تاريخ البدء (افتراضي: الآن)
            expires_at: تاريخ الانتهاء (افتراضي: بعد 30 يوم)

        Returns:
            كائن Subscription المحدث أو None
        """
        now = datetime.now()

        if starts_at is None:
            starts_at = now

        if expires_at is None:
            expires_at = starts_at + timedelta(days=30)

        logger.info(
            "subscription_repo_activate",
            extra={
                "subscription_id": subscription_id,
                "starts_at": starts_at,
                "expires_at": expires_at,
            },
        )

        data: SubscriptionUpdateData = {
            "status": "active",
            "starts_at": starts_at,
            "expires_at": expires_at,
        }

        return await self.update(
            id=subscription_id,
            data=data,
        )

    # ==============================================
    # CANCEL
    # ==============================================

    async def cancel(
        self,
        *,
        subscription_id: int,
    ) -> Optional[Subscription]:
        """
        إلغاء الاشتراك.

        Args:
            subscription_id: معرف الاشتراك

        Returns:
            كائن Subscription المحدث أو None
        """
        logger.info(
            "subscription_repo_cancel",
            extra={"subscription_id": subscription_id},
        )

        return await self.update_status(
            subscription_id=subscription_id,
            status="cancelled",
        )

    # ==============================================
    # EXPIRE
    # ==============================================

    async def expire(
        self,
        *,
        subscription_id: int,
    ) -> Optional[Subscription]:
        """
        تعيين الاشتراك كمنتهي.

        Args:
            subscription_id: معرف الاشتراك

        Returns:
            كائن Subscription المحدث أو None
        """
        logger.info(
            "subscription_repo_expire",
            extra={"subscription_id": subscription_id},
        )

        return await self.update_status(
            subscription_id=subscription_id,
            status="expired",
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
        حساب عدد الاشتراكات حسب الحالة.

        Args:
            status: حالة الاشتراك

        Returns:
            عدد الاشتراكات
        """
        return await self.count(filters={"status": status})

    # ==============================================
    # COUNT ACTIVE
    # ==============================================

    async def count_active(
        self,
    ) -> int:
        """
        حساب عدد الاشتراكات النشطة.

        Returns:
            عدد الاشتراكات النشطة
        """
        return await self.count(filters={"status": "active"})
