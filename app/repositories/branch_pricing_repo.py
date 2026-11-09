# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# BRANCH PRICING REPOSITORY
# Query configured branch tariffs and delegate progressive pricing through the shared
# rules.
# ==============================================

"""Query configured branch tariffs and delegate progressive pricing through the shared rules."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from decimal import Decimal
from typing import (
    Any,
    TypeAlias,
)

from sqlalchemy import (
    and_,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.feature_pricing import BranchPricing
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# Describe shared input, update and result structures for this module.
# ==============================================

BranchPricingData: TypeAlias = dict[str, Any]
BranchPricingUpdateData: TypeAlias = dict[str, Any]
BranchPricingList: TypeAlias = list[BranchPricing]


# ==============================================
# 💰 BRANCH PRICING REPOSITORY
# مستودع تسعير الفروع - يوفر عمليات خاصة بتسعير الفروع.
# ==============================================


class BranchPricingRepository(
    BaseRepository[
        BranchPricing,
        BranchPricingData,
        BranchPricingUpdateData,
    ]
):
    """
    مستودع تسعير الفروع - يوفر عمليات خاصة بتسعير الفروع.

    مسؤول عن:
        - عمليات CRUD الأساسية لتسعير الفروع
        - البحث عن قواعد التسعير النشطة
        - حساب تكلفة الفروع بناءً على عددها

    Attributes:
        model: نموذج BranchPricing
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    # ==============================================
    # INIT
    # تهيئة مستودع تسعير الفروع.
    # ==============================================

    def __init__(
        self,
        *,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع تسعير الفروع.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(BranchPricing, session)

    # ==============================================
    # 📖 QUERIES
    # Read persisted records through the existing repository selection rules.
    # ==============================================

    # ==============================================
    # GET ACTIVE
    # الحصول على قواعد تسعير الفروع النشطة.
    # ==============================================

    async def get_active(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> BranchPricingList:
        """
        الحصول على قواعد تسعير الفروع النشطة.

        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة قواعد تسعير الفروع النشطة
        """
        try:
            query = (
                select(self.model)
                .where(self.model.active == True)
                .order_by(self.model.min_branches.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "branch_pricing_repo_get_active_failed",
                extra={"error": str(e)},
            )
            raise

    # ==============================================
    # GET RULE FOR BRANCHES
    # الحصول على قاعدة تسعير تناسب عدد فروع معين.
    # ==============================================

    async def get_rule_for_branches(
        self,
        *,
        branches_count: int,
        plan_id: int | None = None,
    ) -> BranchPricing | None:
        """
        الحصول على قاعدة تسعير تناسب عدد فروع معين.

        Args:
            branches_count: عدد الفروع

        Returns:
            كائن BranchPricing أو None
        """
        try:
            query = (
                select(self.model)
                .where(
                    and_(
                        self.model.active == True,
                        (
                            self.model.plan_id.is_(None)
                            if plan_id is None
                            else (
                                self.model.plan_id.is_(None)
                                | (self.model.plan_id == plan_id)
                            )
                        ),
                        self.model.min_branches <= branches_count,
                        or_(
                            self.model.max_branches.is_(None),
                            self.model.max_branches >= branches_count,
                        ),
                    ),
                )
                .order_by(
                    self.model.plan_id.is_not(None).desc(),
                    self.model.min_branches.desc(),
                    self.model.id.desc(),
                )
                .limit(1)
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "branch_pricing_repo_get_rule_for_branches_failed",
                extra={
                    "branches_count": branches_count,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # CALCULATE COST
    # Delegate progressive branch charging to the configured shared pricing rules.
    # ==============================================

    async def calculate_cost(
        self,
        *,
        branches_count: int,
    ) -> Decimal:
        """Delegate progressive branch charging to the configured shared pricing rules."""

        from app.services.business.subscription_branch_pricing import branch_breakdown

        return (
            await branch_breakdown(session=self.session, branches_count=branches_count)
        )[0]

    # ==============================================
    # ✏️ UPDATES
    # تحديث سعر الفرع الإضافي.
    # ==============================================

    # ==============================================
    # UPDATE PRICE
    # تحديث سعر الفرع الإضافي.
    # ==============================================

    async def update_price(
        self,
        *,
        pricing_id: int,
        price_per_branch: float,
    ) -> BranchPricing | None:
        """
        تحديث سعر الفرع الإضافي.

        Args:
            pricing_id: معرف قاعدة التسعير
            price_per_branch: السعر الجديد لكل فرع إضافي

        Returns:
            كائن BranchPricing المحدث أو None
        """
        logger.info(
            "branch_pricing_repo_update_price",
            extra={
                "pricing_id": pricing_id,
                "price_per_branch": price_per_branch,
            },
        )

        return await self.update(
            id=pricing_id,
            data={"price_per_branch": price_per_branch},
        )

    # ==============================================
    # ACTIVATE
    # تفعيل قاعدة تسعير.
    # ==============================================

    async def activate(
        self,
        *,
        pricing_id: int,
    ) -> BranchPricing | None:
        """
        تفعيل قاعدة تسعير.

        Args:
            pricing_id: معرف قاعدة التسعير

        Returns:
            كائن BranchPricing المحدث أو None
        """
        logger.info(
            "branch_pricing_repo_activate",
            extra={"pricing_id": pricing_id},
        )

        return await self.update(
            id=pricing_id,
            data={"active": True},
        )

    # ==============================================
    # DEACTIVATE
    # إلغاء تفعيل قاعدة تسعير.
    # ==============================================

    async def deactivate(
        self,
        *,
        pricing_id: int,
    ) -> BranchPricing | None:
        """
        إلغاء تفعيل قاعدة تسعير.

        Args:
            pricing_id: معرف قاعدة التسعير

        Returns:
            كائن BranchPricing المحدث أو None
        """
        logger.info(
            "branch_pricing_repo_deactivate",
            extra={"pricing_id": pricing_id},
        )

        return await self.update(
            id=pricing_id,
            data={"active": False},
        )
