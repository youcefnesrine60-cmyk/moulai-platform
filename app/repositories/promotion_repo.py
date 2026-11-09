# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PROMOTION REPOSITORY
# Select applicable dated campaigns with deterministic rate and priority ordering.
# ==============================================

"""Select applicable dated campaigns with deterministic rate and priority ordering."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from datetime import (
    UTC,
    datetime,
)
from typing import (
    Any,
    TypeAlias,
)

from sqlalchemy import (
    Select,
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
# Describe shared input, update and result structures for this module.
# ==============================================

PromotionData: TypeAlias = dict[str, Any]
PromotionUpdateData: TypeAlias = dict[str, Any]
PromotionList: TypeAlias = list[Promotion]


# ==============================================
# 🎉 PROMOTION REPOSITORY
# مستودع العروض الترويجية - يوفر عمليات خاصة بالعروض الترويجية.
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
    # INIT
    # تهيئة مستودع العروض الترويجية.
    # ==============================================

    def __init__(
        self,
        *,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع العروض الترويجية.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Promotion, session)

    # ==============================================
    # 🔍 BASE QUERY
    # بناء الاستعلام الأساسي للعروض الترويجية.
    # ==============================================

    def _build_base_query(self) -> Select[tuple[Promotion]]:
        """
        بناء الاستعلام الأساسي للعروض الترويجية.

        Returns:
            Select: استعلام SQLAlchemy الأساسي
        """
        return select(self.model)

    # ==============================================
    # 📖 QUERIES
    # Read persisted records through the existing repository selection rules.
    # ==============================================

    # ==============================================
    # GET ACTIVE PROMOTIONS
    # الحصول على العروض الترويجية النشطة حالياً.
    # ==============================================

    async def get_active_promotions(
        self,
        *,
        now: datetime | None = None,
        restaurant_id: int | None = None,
        owner_id: int | None = None,
        plan_id: int | None = None,
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
                        (
                            self.model.owner_id.is_(None)
                            if owner_id is None
                            else (
                                self.model.owner_id.is_(None)
                                | (self.model.owner_id == owner_id)
                            )
                        ),
                        (
                            self.model.plan_id.is_(None)
                            if plan_id is None
                            else (
                                self.model.plan_id.is_(None)
                                | (self.model.plan_id == plan_id)
                            )
                        ),
                        (
                            self.model.restaurant_id.is_(None)
                            if restaurant_id is None
                            else (
                                self.model.restaurant_id.is_(None)
                                | (self.model.restaurant_id == restaurant_id)
                            )
                        ),
                        or_(
                            self.model.starts_at.is_(None),
                            self.model.starts_at <= current_time,
                        ),
                        or_(
                            self.model.expires_at.is_(None),
                            self.model.expires_at > current_time,
                        ),
                    ),
                )
                .order_by(
                    self.model.discount_percent.desc(),
                    self.model.priority.desc(),
                    self.model.id.asc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            rows = list(result.scalars().all())
            return rows

        except Exception as e:
            logger.exception(
                "promotion_repo_get_active_failed",
                extra={"error": str(e)},
            )
            raise

    # ==============================================
    # GET ALL ORDERED
    # الحصول على جميع العروض الترويجية مرتبة حسب المعرف تنازلياً.
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
    # الحصول على العروض الترويجية لمطعم معين.
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
    # البحث في العروض الترويجية بالاسم.
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

    # ==============================================
    # ✏️ MUTATIONS
    # Group persistence changes while retaining the caller's transaction contract.
    # ==============================================

    # ==============================================
    # ACTIVATE PROMOTION
    # تفعيل عرض ترويجي.
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
    # إلغاء تفعيل عرض ترويجي.
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
    # تحديث نسبة الخصم لعرض ترويجي.
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

    # ==============================================
    # 📊 STATISTICS
    # Aggregate persisted counts and values through the existing query paths.
    # ==============================================

    # ==============================================
    # COUNT BY RESTAURANT
    # حساب عدد العروض الترويجية لمطعم معين.
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
