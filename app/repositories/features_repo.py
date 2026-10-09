# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🧩 FEATURE REPOSITORY
# عمليات قاعدة البيانات للميزات باستخدام SQLAlchemy
# Async SQLAlchemy Version
# ==============================================

"""MoulAI operational module for features repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.subscription import Feature
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

FeatureData = Dict[str, Any]
FeatureUpdateData = Dict[str, Any]
FeatureList = List[Feature]

# ==============================================
# 🧩 FEATURE REPOSITORY
# ==============================================


class FeatureRepository(
    BaseRepository[
        Feature,
        FeatureData,
        FeatureUpdateData,
    ]
):
    """
    مستودع الميزات - يوفر عمليات خاصة بالميزات.

    مسؤول عن:
        - عمليات CRUD الأساسية للميزات
        - البحث بالكود
        - البحث بالاسم (بحث جزئي)
        - التحقق من وجود الكود

    Attributes:
        model: نموذج Feature
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
        تهيئة مستودع الميزات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Feature, session)

    # ==========================================
    # 🔍 BASE QUERY
    # ==========================================

    def _build_base_query(self):
        """
        بناء الاستعلام الأساسي للميزات.

        Returns:
            Select: استعلام SQLAlchemy الأساسي
        """
        return select(self.model)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY CODE
    # ==============================================

    async def get_by_code(
        self,
        *,
        code: str,
    ) -> Optional[Feature]:
        """
        الحصول على ميزة بواسطة الكود.

        Args:
            code: كود الميزة (فريد)

        Returns:
            كائن Feature أو None
        """
        try:
            query = self._build_base_query().where(self.model.code == code).limit(1)

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "feature_repo_get_by_code_failed",
                extra={
                    "feature_code": code,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY CODES
    # ==============================================

    async def get_by_codes(
        self,
        *,
        codes: List[str],
    ) -> FeatureList:
        """
        الحصول على ميزات بواسطة قائمة أكواد.

        Args:
            codes: قائمة أكواد الميزات

        Returns:
            قائمة الميزات
        """
        try:
            query = (
                self._build_base_query()
                .where(self.model.code.in_(codes))
                .order_by(self.model.id.asc())
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "feature_repo_get_by_codes_failed",
                extra={
                    "feature_codes": codes,
                    "error": str(e),
                },
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
    ) -> FeatureList:
        """
        الحصول على جميع الميزات مرتبة حسب المعرف.

        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الميزات
        """
        try:
            query = (
                self._build_base_query()
                .order_by(self.model.id.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "feature_repo_get_all_ordered_failed",
                extra={"error": str(e)},
            )
            raise

    # ==============================================
    # SEARCH BY NAME
    # ==============================================

    async def search_by_name(
        self,
        *,
        name: str,
        skip: int = 0,
        limit: int = 100,
    ) -> FeatureList:
        """
        البحث عن الميزات بالاسم (بحث جزئي).

        Args:
            name: جزء من اسم الميزة
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الميزات المطابقة
        """
        try:
            query = (
                self._build_base_query()
                .where(self.model.name.ilike(f"%{name}%"))
                .order_by(self.model.name.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "feature_repo_search_by_name_failed",
                extra={
                    "feature_name": name,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✅ EXISTENCE CHECKS
    # ==========================================

    # ==============================================
    # CODE EXISTS
    # ==============================================

    async def code_exists(
        self,
        *,
        code: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """
        التحقق من وجود كود الميزة.

        Args:
            code: كود الميزة
            exclude_id: معرف لاستثنائه من التحقق (للتحديث)

        Returns:
            True إذا كان الكود موجوداً
        """
        try:
            query = select(self.model.id).where(self.model.code == code)

            if exclude_id is not None:
                query = query.where(self.model.id != exclude_id)

            query = query.limit(1)

            result = await self.session.execute(query)

            return result.scalar_one_or_none() is not None

        except Exception as e:
            logger.exception(
                "feature_repo_code_exists_failed",
                extra={
                    "feature_code": code,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT ALL
    # ==============================================

    async def count_all(self) -> int:
        """
        حساب إجمالي عدد الميزات.

        Returns:
            عدد الميزات
        """
        return await self.count()


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة (Psycopg3)
# ==============================================

# ==============================================
# CREATE FEATURE (COMPATIBILITY)
# ==============================================


async def create_feature(
    *,
    code: str,
    name: str,
    description: Optional[str] = None,
    session: AsyncSession,
) -> int:
    """
    إنشاء ميزة جديدة (دالة متوافقة مع الإصدار القديم).

    Args:
        code: كود الميزة
        name: اسم الميزة
        description: وصف الميزة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف الميزة
    """
    repo = FeatureRepository(session=session)

    data: FeatureData = {
        "code": code,
        "name": name,
        "description": description,
    }

    feature = await repo.create(data=data)

    logger.info(
        "feature_created",
        extra={
            "feature_id": feature.id,
            "feature_code": code,
        },
    )

    return feature.id


# ==============================================
# GET FEATURE BY ID (COMPATIBILITY)
# ==============================================


async def get_feature_by_id(
    *,
    feature_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على ميزة بالمعرف (دالة متوافقة مع الإصدار القديم).

    Args:
        feature_id: معرف الميزة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات الميزة أو None
    """
    repo = FeatureRepository(session=session)

    feature = await repo.get_by_id(id=feature_id)

    if not feature:
        logger.warning(
            "feature_not_found",
            extra={"feature_id": feature_id},
        )
        return None

    return {
        "id": feature.id,
        "code": feature.code,
        "name": feature.name,
        "description": feature.description,
    }


# ==============================================
# GET FEATURE BY CODE (COMPATIBILITY)
# ==============================================


async def get_feature_by_code(
    *,
    code: str,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على ميزة بالكود (دالة متوافقة مع الإصدار القديم).

    Args:
        code: كود الميزة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات الميزة أو None
    """
    repo = FeatureRepository(session=session)

    feature = await repo.get_by_code(code=code)

    if not feature:
        return None

    return {
        "id": feature.id,
        "code": feature.code,
        "name": feature.name,
        "description": feature.description,
    }


# ==============================================
# GET ALL FEATURES (COMPATIBILITY)
# ==============================================


async def get_all_features(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على جميع الميزات (دالة متوافقة مع الإصدار القديم).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        قائمة الميزات
    """
    repo = FeatureRepository(session=session)

    features = await repo.get_all_ordered(
        skip=skip,
        limit=limit,
    )

    result = []

    for feature in features:
        result.append(
            {
                "id": feature.id,
                "code": feature.code,
                "name": feature.name,
                "description": feature.description,
            }
        )

    logger.info(
        "features_fetched",
        extra={"count": len(result)},
    )

    return result


# ==============================================
# UPDATE FEATURE (COMPATIBILITY)
# ==============================================


async def update_feature(
    *,
    feature_id: int,
    name: str,
    description: Optional[str],
    session: AsyncSession,
) -> None:
    """
    تحديث ميزة (دالة متوافقة مع الإصدار القديم).

    Args:
        feature_id: معرف الميزة
        name: الاسم الجديد
        description: الوصف الجديد
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = FeatureRepository(session=session)

    await repo.update(
        id=feature_id,
        data={
            "name": name,
            "description": description,
        },
    )

    logger.info(
        "feature_updated",
        extra={"feature_id": feature_id},
    )


# ==============================================
# DELETE FEATURE (COMPATIBILITY)
# ==============================================


async def delete_feature(
    *,
    feature_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف ميزة (دالة متوافقة مع الإصدار القديم).

    Args:
        feature_id: معرف الميزة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = FeatureRepository(session=session)

    await repo.delete(id=feature_id)

    logger.info(
        "feature_deleted",
        extra={"feature_id": feature_id},
    )
