# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🎉 PROMOTION REPOSITORY
# عمليات قاعدة البيانات للعروض الترويجية باستخدام SQLAlchemy
# Async SQLAlchemy Version
# ==============================================

"""MoulAI operational module for promotion repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from datetime import UTC, datetime
from typing import (
    Any,
)

from sqlalchemy import (
    and_,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.loyalty_discount import Promotion
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

PromotionData = dict[str, Any]
PromotionUpdateData = dict[str, Any]
PromotionList = list[Promotion]

# ==============================================
# 🎉 PROMOTION REPOSITORY
# ==============================================


class PromotionRepository(
    BaseRepository[
        Promotion,
        PromotionData,
        PromotionUpdateData,
    ]
):
    """
    مستودع العروض الترويجية - يوفر عمليات خاصة بالعروض الترويجية.

    مسؤول عن:
        - عمليات CRUD الأساسية للعروض الترويجية
        - جلب العروض النشطة (حسب التاريخ + active)
        - جلب العروض حسب المطعم
        - البحث في العروض
        - تفعيل/إلغاء تفعيل العروض

    Attributes:
        model: نموذج Promotion
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
        تهيئة مستودع العروض الترويجية.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Promotion, session)

    # ==========================================
    # 🔍 BASE QUERY
    # ==========================================

    def _build_base_query(self):
        """
        بناء الاستعلام الأساسي للعروض الترويجية.

        Returns:
            Select: استعلام SQLAlchemy الأساسي
        """
        return select(self.model)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET ACTIVE PROMOTIONS
    # ==============================================

    async def get_active_promotions(
        self,
        *,
        now: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> PromotionList:
        """
        الحصول على العروض الترويجية النشطة حالياً.

        Args:
            now: الوقت الحالي (افتراضي: now())
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة العروض النشطة
        """
        try:
            current_time = now or datetime.now(UTC).replace(tzinfo=None)

            query = (
                self._build_base_query()
                .where(
                    and_(
                        self.model.active.is_(True),
                        or_(
                            self.model.starts_at.is_(None),
                            self.model.starts_at <= current_time,
                        ),
                        or_(
                            self.model.expires_at.is_(None),
                            self.model.expires_at >= current_time,
                        ),
                    ),
                )
                .order_by(self.model.id.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "promotion_repo_get_active_failed",
                extra={"error": str(e)},
            )
            raise

    # ==============================================
    # GET ALL ORDERED
    # ==============================================

    async def get_all_ordered(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> PromotionList:
        """
        الحصول على جميع العروض الترويجية مرتبة حسب المعرف تنازلياً.

        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة العروض
        """
        try:
            query = (
                self._build_base_query()
                .order_by(self.model.id.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "promotion_repo_get_all_failed",
                extra={"error": str(e)},
            )
            raise

    # ==============================================
    # GET BY RESTAURANT
    # ==============================================

    async def get_by_restaurant(
        self,
        *,
        restaurant_id: int,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> PromotionList:
        """
        الحصول على العروض الترويجية لمطعم معين.

        Args:
            restaurant_id: معرف المطعم
            only_active: جلب العروض النشطة فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة العروض
        """
        try:
            query = self._build_base_query().where(
                self.model.restaurant_id == restaurant_id
            )

            if only_active:
                query = query.where(self.model.active.is_(True))

            query = query.order_by(self.model.id.desc()).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "promotion_repo_get_by_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # SEARCH PROMOTIONS
    # ==============================================

    async def search_promotions(
        self,
        *,
        search_query: str,
        restaurant_id: int | None = None,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> PromotionList:
        """
        البحث في العروض الترويجية بالاسم.

        Args:
            search_query: نص البحث في اسم العرض
            restaurant_id: معرف المطعم (اختياري)
            only_active: جلب العروض النشطة فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة العروض المطابقة
        """
        try:
            conditions = [
                self.model.name.ilike(f"%{search_query}%"),
            ]

            if restaurant_id is not None:
                conditions.append(
                    self.model.restaurant_id == restaurant_id,
                )

            if only_active:
                conditions.append(self.model.active.is_(True))

            query = (
                self._build_base_query()
                .where(and_(*conditions))
                .order_by(self.model.id.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "promotion_repo_search_failed",
                extra={
                    "search_query": search_query,
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ MUTATIONS
    # ==============================================

    # ==============================================
    # ACTIVATE PROMOTION
    # ==============================================

    async def activate(
        self,
        *,
        promotion_id: int,
    ) -> Promotion | None:
        """
        تفعيل عرض ترويجي.

        Args:
            promotion_id: معرف العرض

        Returns:
            كائن Promotion المحدث أو None
        """
        logger.info(
            "promotion_repo_activate",
            extra={"promotion_id": promotion_id},
        )

        return await self.update(
            id=promotion_id,
            data={"active": True},
        )

    # ==============================================
    # DEACTIVATE PROMOTION
    # ==============================================

    async def deactivate(
        self,
        *,
        promotion_id: int,
    ) -> Promotion | None:
        """
        إلغاء تفعيل عرض ترويجي.

        Args:
            promotion_id: معرف العرض

        Returns:
            كائن Promotion المحدث أو None
        """
        logger.info(
            "promotion_repo_deactivate",
            extra={"promotion_id": promotion_id},
        )

        return await self.update(
            id=promotion_id,
            data={"active": False},
        )

    # ==============================================
    # UPDATE DISCOUNT PERCENT
    # ==============================================

    async def update_discount_percent(
        self,
        *,
        promotion_id: int,
        discount_percent: float,
    ) -> Promotion | None:
        """
        تحديث نسبة الخصم لعرض ترويجي.

        Args:
            promotion_id: معرف العرض
            discount_percent: نسبة الخصم الجديدة

        Returns:
            كائن Promotion المحدث أو None
        """
        logger.info(
            "promotion_repo_update_discount",
            extra={
                "promotion_id": promotion_id,
                "discount_percent": discount_percent,
            },
        )

        return await self.update(
            id=promotion_id,
            data={"discount_percent": discount_percent},
        )

    # ==========================================
    # 📊 STATISTICS
    # ==============================================

    # ==============================================
    # COUNT BY RESTAURANT
    # ==============================================

    async def count_by_restaurant(
        self,
        *,
        restaurant_id: int,
        only_active: bool = True,
    ) -> int:
        """
        حساب عدد العروض الترويجية لمطعم معين.

        Args:
            restaurant_id: معرف المطعم
            only_active: حساب العروض النشطة فقط

        Returns:
            عدد العروض
        """
        filters = {"restaurant_id": restaurant_id}

        if only_active:
            filters["active"] = True

        return await self.count(filters=filters)
