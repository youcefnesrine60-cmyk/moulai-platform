# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 💰 BRANCH PRICING REPOSITORY
# عمليات قاعدة البيانات لتسعير الفروع باستخدام SQLAlchemy
# ==============================================

"""MoulAI operational module for branch pricing repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

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
from app.models.feature_pricing import BranchPricing
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

BranchPricingData = Dict[str, Any]
BranchPricingUpdateData = Dict[str, Any]
BranchPricingList = List[BranchPricing]

# ==============================================
# 💰 BRANCH PRICING REPOSITORY
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
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع تسعير الفروع.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(BranchPricing, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET ACTIVE
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
    # ==============================================

    async def get_rule_for_branches(
        self,
        *,
        branches_count: int,
    ) -> Optional[BranchPricing]:
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
                        self.model.min_branches <= branches_count,
                        or_(
                            self.model.max_branches.is_(None),
                            self.model.max_branches >= branches_count,
                        ),
                    ),
                )
                .order_by(
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
    # ==============================================

    async def calculate_cost(
        self,
        *,
        branches_count: int,
    ) -> float:
        """
        حساب تكلفة الفروع بناءً على عددها.

        Args:
            branches_count: عدد الفروع

        Returns:
            التكلفة الإجمالية
        """
        try:
            # إذا كان عدد الفروع 1 أو أقل، التكلفة 0
            if branches_count <= 1:
                return 0.0

            # الحصول على قاعدة التسعير المناسبة
            rule = await self.get_rule_for_branches(
                branches_count=branches_count,
            )

            if not rule:
                logger.warning(
                    "branch_pricing_repo_no_rule_found",
                    extra={"branches_count": branches_count},
                )
                return 0.0

            # حساب التكلفة: (عدد الفروع - 1) * سعر الفرع الإضافي
            extra_branches = branches_count - 1
            cost = extra_branches * float(rule.price_per_branch)

            logger.info(
                "branch_pricing_repo_calculate_cost",
                extra={
                    "branches_count": branches_count,
                    "extra_branches": extra_branches,
                    "price_per_branch": float(rule.price_per_branch),
                    "cost": cost,
                },
            )

            return cost

        except Exception as e:
            logger.exception(
                "branch_pricing_repo_calculate_cost_failed",
                extra={
                    "branches_count": branches_count,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ UPDATES
    # ==========================================

    # ==============================================
    # UPDATE PRICE
    # ==============================================

    async def update_price(
        self,
        *,
        pricing_id: int,
        price_per_branch: float,
    ) -> Optional[BranchPricing]:
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
    # ==============================================

    async def activate(
        self,
        *,
        pricing_id: int,
    ) -> Optional[BranchPricing]:
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
    # ==============================================

    async def deactivate(
        self,
        *,
        pricing_id: int,
    ) -> Optional[BranchPricing]:
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


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE BRANCH PRICING (COMPATIBILITY)
# ==============================================


async def create_branch_pricing(
    *,
    min_branches: int,
    max_branches: Optional[int],
    price_per_branch: float,
    active: bool = True,
    session: AsyncSession,
) -> int:
    """
    إنشاء قاعدة تسعير فروع جديدة (دالة متوافقة مع الإصدار القديم).

    Args:
        min_branches: الحد الأدنى لعدد الفروع
        max_branches: الحد الأقصى لعدد الفروع
        price_per_branch: سعر الفرع الإضافي
        active: حالة النشاط
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف قاعدة التسعير
    """
    repo = BranchPricingRepository(session=session)

    data: BranchPricingData = {
        "min_branches": min_branches,
        "max_branches": max_branches,
        "price_per_branch": price_per_branch,
        "active": active,
    }

    pricing = await repo.create(data=data)

    logger.info(
        "branch_pricing_created",
        extra={"pricing_id": pricing.id},
    )

    return pricing.id


# ==============================================
# GET BRANCH PRICING BY ID (COMPATIBILITY)
# ==============================================


async def get_branch_pricing_by_id(
    *,
    pricing_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على قاعدة تسعير بالمعرف (دالة متوافقة مع الإصدار القديم).

    Args:
        pricing_id: معرف قاعدة التسعير
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات قاعدة التسعير أو None
    """
    repo = BranchPricingRepository(session=session)

    pricing = await repo.get_by_id(id=pricing_id)

    if not pricing:
        return None

    return {
        "id": pricing.id,
        "min_branches": pricing.min_branches,
        "max_branches": pricing.max_branches,
        "price_per_branch": float(pricing.price_per_branch),
        "active": pricing.active,
        "created_at": pricing.created_at,
    }


# ==============================================
# GET ACTIVE BRANCH PRICING (COMPATIBILITY)
# ==============================================


async def get_active_branch_pricing(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على قواعد تسعير الفروع النشطة (دالة متوافقة مع الإصدار القديم).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        قائمة قواعد تسعير الفروع النشطة
    """
    repo = BranchPricingRepository(session=session)

    pricings = await repo.get_active(
        skip=skip,
        limit=limit,
    )

    result = []

    for pricing in pricings:
        result.append(
            {
                "id": pricing.id,
                "min_branches": pricing.min_branches,
                "max_branches": pricing.max_branches,
                "price_per_branch": float(pricing.price_per_branch),
                "active": pricing.active,
                "created_at": pricing.created_at,
            }
        )

    return result


# ==============================================
# GET BRANCH PRICING RULE (COMPATIBILITY)
# ==============================================


async def get_branch_pricing_rule(
    *,
    branches_count: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على قاعدة تسعير تناسب عدد فروع معين (دالة متوافقة مع الإصدار القديم).

    Args:
        branches_count: عدد الفروع
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات قاعدة التسعير أو None
    """
    repo = BranchPricingRepository(session=session)

    pricing = await repo.get_rule_for_branches(
        branches_count=branches_count,
    )

    if not pricing:
        return None

    return {
        "id": pricing.id,
        "min_branches": pricing.min_branches,
        "max_branches": pricing.max_branches,
        "price_per_branch": float(pricing.price_per_branch),
        "active": pricing.active,
        "created_at": pricing.created_at,
    }


# ==============================================
# CALCULATE BRANCH COST (COMPATIBILITY)
# ==============================================


async def calculate_branch_cost(
    *,
    branches_count: int,
    session: AsyncSession,
) -> float:
    """
    حساب تكلفة الفروع (دالة متوافقة مع الإصدار القديم).

    Args:
        branches_count: عدد الفروع
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        التكلفة الإجمالية
    """
    repo = BranchPricingRepository(session=session)

    return await repo.calculate_cost(
        branches_count=branches_count,
    )


# ==============================================
# UPDATE BRANCH PRICING PRICE (COMPATIBILITY)
# ==============================================


async def update_branch_pricing_price(
    *,
    pricing_id: int,
    price_per_branch: float,
    session: AsyncSession,
) -> None:
    """
    تحديث سعر الفرع الإضافي (دالة متوافقة مع الإصدار القديم).

    Args:
        pricing_id: معرف قاعدة التسعير
        price_per_branch: السعر الجديد لكل فرع إضافي
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = BranchPricingRepository(session=session)

    await repo.update_price(
        pricing_id=pricing_id,
        price_per_branch=price_per_branch,
    )

    logger.info(
        "branch_pricing_price_updated",
        extra={
            "pricing_id": pricing_id,
            "price_per_branch": price_per_branch,
        },
    )


# ==============================================
# ACTIVATE BRANCH PRICING (COMPATIBILITY)
# ==============================================


async def activate_branch_pricing(
    *,
    pricing_id: int,
    session: AsyncSession,
) -> None:
    """
    تفعيل قاعدة تسعير (دالة متوافقة مع الإصدار القديم).

    Args:
        pricing_id: معرف قاعدة التسعير
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = BranchPricingRepository(session=session)

    await repo.activate(pricing_id=pricing_id)

    logger.info(
        "branch_pricing_activated",
        extra={"pricing_id": pricing_id},
    )


# ==============================================
# DEACTIVATE BRANCH PRICING (COMPATIBILITY)
# ==============================================


async def deactivate_branch_pricing(
    *,
    pricing_id: int,
    session: AsyncSession,
) -> None:
    """
    إلغاء تفعيل قاعدة تسعير (دالة متوافقة مع الإصدار القديم).

    Args:
        pricing_id: معرف قاعدة التسعير
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = BranchPricingRepository(session=session)

    await repo.deactivate(pricing_id=pricing_id)

    logger.info(
        "branch_pricing_deactivated",
        extra={"pricing_id": pricing_id},
    )
