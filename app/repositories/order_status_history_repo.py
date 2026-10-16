# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / REPOSITORIES / ORDER STATUS HISTORY REPO
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for order status history repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================
# ==============================================
# 📜 ORDER STATUS HISTORY REPOSITORY
# عمليات قاعدة البيانات لتاريخ حالات الطلبات باستخدام SQLAlchemy
# ==============================================
from typing import (
    Any,
)

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.core.logger import logger
from app.models.order_item import OrderStatusHistory
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

OrderStatusHistoryData = dict[str, Any]
OrderStatusHistoryList = list[OrderStatusHistory]
OrderStatusTimeline = list[dict[str, Any]]

# ==============================================
# 📜 ORDER STATUS HISTORY REPOSITORY
# ==============================================


class OrderStatusHistoryRepository(
    BaseRepository[
        OrderStatusHistory,
        OrderStatusHistoryData,
        OrderStatusHistoryData,
    ]
):
    """
    مستودع تاريخ حالات الطلبات - يوفر عمليات خاصة بتاريخ حالات الطلبات.

    مسؤول عن:
        - تسجيل تغييرات حالة الطلب
        - استعراض تاريخ حالات الطلب
        - الحصول على آخر تغيير في الحالة
        - إحصائيات تغييرات الحالة

    Attributes:
        model: نموذج OrderStatusHistory
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
        تهيئة مستودع تاريخ حالات الطلبات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(OrderStatusHistory, session)
        self.commit_on_write = False
        self.query_options = [raiseload("*")]

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ORDER ID
    # ==============================================

    async def delete_by_order(self, *, order_id):
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(self.model).where(self.model.order_id == order_id)
        )
        return result.rowcount

    # ==============================================
    # GET BY ORDER ID
    # ==============================================

    async def get_by_order_id(
        self,
        *,
        order_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> OrderStatusHistoryList:
        """
        الحصول على تاريخ حالات طلب معين.

        Args:
            order_id: معرف الطلب
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة تاريخ حالات الطلب
        """
        try:
            query = (
                self._select()
                .where(self.model.order_id == order_id)
                .order_by(self.model.id.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "order_status_history_repo_get_by_order_failed",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET LAST STATUS CHANGE
    # ==============================================

    async def get_last_status_change(
        self,
        *,
        order_id: int,
    ) -> OrderStatusHistory | None:
        """
        الحصول على آخر تغيير في حالة الطلب.

        Args:
            order_id: معرف الطلب

        Returns:
            كائن OrderStatusHistory أو None
        """
        try:
            result = await self.session.execute(
                self._select()
                .where(self.model.order_id == order_id)
                .order_by(self.model.id.desc())
                .limit(1),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "order_status_history_repo_get_last_status_change_failed",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET STATUS TIMELINE
    # ==============================================

    async def get_status_timeline(
        self,
        *,
        order_id: int,
    ) -> OrderStatusTimeline:
        """
        الحصول على الجدول الزمني لحالات الطلب.

        Args:
            order_id: معرف الطلب

        Returns:
            قائمة الحالات مع التواريخ
        """
        try:
            history = await self.get_by_order_id(order_id=order_id)

            result = []

            for entry in history:
                result.append(
                    {
                        "new_status": entry.new_status,
                        "created_at": entry.created_at,
                    }
                )

            return result

        except Exception as e:
            logger.exception(
                "order_status_history_repo_get_status_timeline_failed",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # COUNT STATUS CHANGES
    # ==============================================

    async def count_status_changes(
        self,
        *,
        order_id: int,
    ) -> int:
        """
        حساب عدد تغييرات حالة طلب معين.

        Args:
            order_id: معرف الطلب

        Returns:
            عدد التغييرات
        """
        try:
            result = await self.session.execute(
                select(func.count())
                .select_from(self.model)
                .where(self.model.order_id == order_id),
            )

            return result.scalar_one()

        except Exception as e:
            logger.exception(
                "order_status_history_repo_count_status_changes_failed",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET ORDERS REACHED STATUS
    # ==============================================

    async def get_orders_reached_status(
        self,
        *,
        status: str,
    ) -> list[int]:
        """
        الحصول على معرفات الطلبات التي وصلت إلى حالة معينة.

        Args:
            status: حالة الطلب

        Returns:
            قائمة معرفات الطلبات
        """
        try:
            result = await self.session.execute(
                select(self.model.order_id)
                .where(self.model.new_status == status)
                .distinct()
                .order_by(self.model.order_id),
            )

            return [row[0] for row in result.all()]

        except Exception as e:
            logger.exception(
                "order_status_history_repo_get_orders_reached_status_failed",
                extra={
                    "status": status,
                    "error": str(e),
                },
            )
            raise
