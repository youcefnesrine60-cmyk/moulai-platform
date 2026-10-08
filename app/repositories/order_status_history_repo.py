from sqlalchemy.orm import raiseload, selectinload
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
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.order_item import OrderStatusHistory
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

OrderStatusHistoryData = Dict[str, Any]
OrderStatusHistoryList = List[OrderStatusHistory]
OrderStatusTimeline = List[Dict[str, Any]]

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
        result = await self.session.execute(delete(self.model).where(self.model.order_id == order_id))
        return result.rowcount

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
    ) -> Optional[OrderStatusHistory]:
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
                result.append({
                    "new_status": entry.new_status,
                    "created_at": entry.created_at,
                })

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
    ) -> List[int]:
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


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE STATUS HISTORY (COMPATIBILITY)
# ==============================================

async def create_status_history(
    *,
    order_id: int,
    old_status: Optional[str],
    new_status: str,
    changed_by_employee_id: Optional[int] = None,
    note: Optional[str] = None,
    session: AsyncSession,
) -> None:
    """
    إنشاء سجل تاريخ حالة جديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        old_status: الحالة السابقة
        new_status: الحالة الجديدة
        changed_by_employee_id: معرف الموظف الذي غيّر الحالة
        note: ملاحظة إضافية
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = OrderStatusHistoryRepository(session=session)

    data: OrderStatusHistoryData = {
        "order_id": order_id,
        "old_status": old_status,
        "new_status": new_status,
        "changed_by_employee_id": changed_by_employee_id,
        "note": note,
    }

    await repo.create(data=data)

    logger.info(
        "order_status_history_created",
        extra={
            "order_id": order_id,
            "new_status": new_status,
        },
    )


# ==============================================
# GET ORDER STATUS HISTORY (COMPATIBILITY)
# ==============================================

async def get_order_status_history(
    *,
    order_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على تاريخ حالات طلب معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        قائمة تاريخ حالات الطلب
    """
    repo = OrderStatusHistoryRepository(session=session)

    history = await repo.get_by_order_id(
        order_id=order_id,
        skip=skip,
        limit=limit,
    )

    result = []

    for entry in history:
        result.append({
            "id": entry.id,
            "order_id": entry.order_id,
            "old_status": entry.old_status,
            "new_status": entry.new_status,
            "changed_by_employee_id": entry.changed_by_employee_id,
            "note": entry.note,
            "created_at": entry.created_at,
        })

    return result


# ==============================================
# GET LAST STATUS CHANGE (COMPATIBILITY)
# ==============================================

async def get_last_status_change(
    *,
    order_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على آخر تغيير في حالة الطلب (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        آخر تغيير في حالة الطلب أو None
    """
    repo = OrderStatusHistoryRepository(session=session)

    entry = await repo.get_last_status_change(order_id=order_id)

    if not entry:
        return None

    return {
        "id": entry.id,
        "order_id": entry.order_id,
        "old_status": entry.old_status,
        "new_status": entry.new_status,
        "changed_by_employee_id": entry.changed_by_employee_id,
        "note": entry.note,
        "created_at": entry.created_at,
    }


# ==============================================
# GET STATUS TIMELINE (COMPATIBILITY)
# ==============================================

async def get_status_timeline(
    *,
    order_id: int,
    session: AsyncSession,
) -> OrderStatusTimeline:
    """
    الحصول على الجدول الزمني لحالات الطلب (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        الجدول الزمني للحالات
    """
    repo = OrderStatusHistoryRepository(session=session)

    return await repo.get_status_timeline(order_id=order_id)


# ==============================================
# COUNT STATUS CHANGES (COMPATIBILITY)
# ==============================================

async def count_status_changes(
    *,
    order_id: int,
    session: AsyncSession,
) -> int:
    """
    حساب عدد تغييرات حالة طلب معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        عدد التغييرات
    """
    repo = OrderStatusHistoryRepository(session=session)

    return await repo.count_status_changes(order_id=order_id)


# ==============================================
# GET ORDERS REACHED STATUS (COMPATIBILITY)
# ==============================================

async def get_orders_reached_status(
    *,
    status: str,
    session: AsyncSession,
) -> List[int]:
    """
    الحصول على معرفات الطلبات التي وصلت إلى حالة معينة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        status: حالة الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قائمة معرفات الطلبات
    """
    repo = OrderStatusHistoryRepository(session=session)

    return await repo.get_orders_reached_status(status=status)


# ==============================================
# 🔄 TRANSACTION FUNCTIONS (للتوافق مع الكود القديم)
# ==============================================

# ==============================================
# CREATE STATUS HISTORY TX
# ==============================================

async def create_status_history_tx(
    conn: AsyncSession,
    *,
    order_id: int,
    old_status: Optional[str],
    new_status: str,
    changed_by_employee_id: Optional[int] = None,
    note: Optional[str] = None,
) -> None:
    """
    إنشاء سجل تاريخ حالة جديد (معاملة) - دالة متوافقة مع الإصدار القديم.
    
    Args:
        conn: جلسة قاعدة البيانات (AsyncSession)
        order_id: معرف الطلب
        old_status: الحالة السابقة
        new_status: الحالة الجديدة
        changed_by_employee_id: معرف الموظف الذي غيّر الحالة
        note: ملاحظة إضافية
    """
    repo = OrderStatusHistoryRepository(conn)

    data: OrderStatusHistoryData = {
        "order_id": order_id,
        "old_status": old_status,
        "new_status": new_status,
        "changed_by_employee_id": changed_by_employee_id,
        "note": note,
    }

    await repo.create(data=data)

    logger.info(
        "order_status_history_created_tx",
        extra={
            "order_id": order_id,
            "new_status": new_status,
        },
    )