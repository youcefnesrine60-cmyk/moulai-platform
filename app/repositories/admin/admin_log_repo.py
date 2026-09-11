# ==============================================
# 📋 ADMIN LOG REPOSITORY
# عمليات قاعدة البيانات لسجل أنشطة المدير باستخدام SQLAlchemy
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
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.admin_log import AdminLog
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

AdminLogData = Dict[str, Any]
AdminLogUpdateData = Dict[str, Any]
AdminLogList = List[AdminLog]
ActionsSummary = List[Dict[str, Any]]

# ==============================================
# 📋 ADMIN LOG REPOSITORY
# ==============================================


class AdminLogRepository(BaseRepository[AdminLog, AdminLogData, AdminLogUpdateData]):
    """
    مستودع سجل أنشطة المدير - يوفر عمليات خاصة بسجل أنشطة المدير.
    
    مسؤول عن:
        - عمليات CRUD الأساسية لسجل الأنشطة
        - البحث والتصفية حسب المدير والإجراء والمورد
        - إحصائيات الأنشطة
    
    Attributes:
        model: نموذج AdminLog
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع سجل أنشطة المدير.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(AdminLog, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ADMIN ID
    # ==============================================

    async def get_by_admin_id(
        self,
        *,
        admin_id: int,
        skip: int = 0,
        limit: int = 100,
        action: Optional[str] = None,
        resource: Optional[str] = None,
    ) -> AdminLogList:
        """
        الحصول على سجل أنشطة مدير معين.
        
        Args:
            admin_id: معرف المدير
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            action: نوع الإجراء (اختياري)
            resource: نوع المورد (اختياري)
            
        Returns:
            قائمة سجل الأنشطة
        """
        try:
            query = select(self.model).where(
                self.model.admin_id == admin_id,
            )

            if action is not None:
                query = query.where(self.model.action == action)

            if resource is not None:
                query = query.where(self.model.resource == resource)

            query = query.order_by(
                self.model.timestamp.desc(),
                self.model.id.desc(),
            ).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "admin_log_repo_get_by_admin_failed",
                extra={
                    "admin_id": admin_id,
                    "action": action,
                    "resource": resource,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY ACTION
    # ==============================================

    async def get_by_action(
        self,
        *,
        action: str,
        skip: int = 0,
        limit: int = 100,
        admin_id: Optional[int] = None,
    ) -> AdminLogList:
        """
        الحصول على سجل الأنشطة حسب نوع الإجراء.
        
        Args:
            action: نوع الإجراء
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            admin_id: معرف المدير (اختياري)
            
        Returns:
            قائمة سجل الأنشطة
        """
        try:
            query = select(self.model).where(
                self.model.action == action,
            )

            if admin_id is not None:
                query = query.where(self.model.admin_id == admin_id)

            query = query.order_by(
                self.model.timestamp.desc(),
                self.model.id.desc(),
            ).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "admin_log_repo_get_by_action_failed",
                extra={
                    "action": action,
                    "admin_id": admin_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY RESOURCE
    # ==============================================

    async def get_by_resource(
        self,
        *,
        resource: str,
        skip: int = 0,
        limit: int = 100,
        resource_id: Optional[int] = None,
    ) -> AdminLogList:
        """
        الحصول على سجل الأنشطة حسب نوع المورد.
        
        Args:
            resource: نوع المورد
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            resource_id: معرف المورد (اختياري)
            
        Returns:
            قائمة سجل الأنشطة
        """
        try:
            query = select(self.model).where(
                self.model.resource == resource,
            )

            if resource_id is not None:
                query = query.where(self.model.resource_id == resource_id)

            query = query.order_by(
                self.model.timestamp.desc(),
                self.model.id.desc(),
            ).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "admin_log_repo_get_by_resource_failed",
                extra={
                    "resource": resource,
                    "resource_id": resource_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY DATE RANGE
    # ==============================================

    async def get_by_date_range(
        self,
        *,
        start_date: datetime,
        end_date: datetime,
        admin_id: Optional[int] = None,
        action: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> AdminLogList:
        """
        الحصول على سجل الأنشطة في نطاق زمني معين.
        
        Args:
            start_date: تاريخ البداية
            end_date: تاريخ النهاية
            admin_id: معرف المدير (اختياري)
            action: نوع الإجراء (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة سجل الأنشطة
        """
        try:
            query = select(self.model).where(
                and_(
                    self.model.timestamp >= start_date,
                    self.model.timestamp <= end_date,
                ),
            )

            if admin_id is not None:
                query = query.where(self.model.admin_id == admin_id)

            if action is not None:
                query = query.where(self.model.action == action)

            query = query.order_by(
                self.model.timestamp.desc(),
                self.model.id.desc(),
            ).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "admin_log_repo_get_by_date_range_failed",
                extra={
                    "start_date": start_date,
                    "end_date": end_date,
                    "admin_id": admin_id,
                    "action": action,
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
        admin_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> AdminLogList:
        """
        البحث في سجل الأنشطة.
        
        Args:
            query: نص البحث
            admin_id: معرف المدير (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة سجل الأنشطة
        """
        try:
            conditions = [
                or_(
                    self.model.action.ilike(f"%{query}%"),
                    self.model.resource.ilike(f"%{query}%"),
                    self.model.details.ilike(f"%{query}%"),
                    self.model.ip_address.ilike(f"%{query}%"),
                ),
            ]

            if admin_id is not None:
                conditions.append(
                    self.model.admin_id == admin_id,
                )

            stmt = (
                select(self.model)
                .where(*conditions)
                .order_by(
                    self.model.timestamp.desc(),
                    self.model.id.desc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "admin_log_repo_search_failed",
                extra={
                    "query": query,
                    "admin_id": admin_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY ADMIN
    # ==============================================

    async def count_by_admin(
        self,
        *,
        admin_id: int,
        action: Optional[str] = None,
    ) -> int:
        """
        حساب عدد سجلات الأنشطة لمدير معين.
        
        Args:
            admin_id: معرف المدير
            action: نوع الإجراء (اختياري)
            
        Returns:
            عدد السجلات
        """
        filters = {"admin_id": admin_id}

        if action is not None:
            filters["action"] = action

        return await self.count(filters=filters)

    # ==============================================
    # COUNT BY ACTION
    # ==============================================

    async def count_by_action(
        self,
        *,
        action: str,
    ) -> int:
        """
        حساب عدد سجلات الأنشطة حسب نوع الإجراء.
        
        Args:
            action: نوع الإجراء
            
        Returns:
            عدد السجلات
        """
        return await self.count(filters={"action": action})

    # ==============================================
    # COUNT BY RESOURCE
    # ==============================================

    async def count_by_resource(
        self,
        *,
        resource: str,
    ) -> int:
        """
        حساب عدد سجلات الأنشطة حسب نوع المورد.
        
        Args:
            resource: نوع المورد
            
        Returns:
            عدد السجلات
        """
        return await self.count(filters={"resource": resource})

    # ==============================================
    # GET ACTIONS SUMMARY
    # ==============================================

    async def get_actions_summary(
        self,
        *,
        admin_id: Optional[int] = None,
        limit: int = 10,
    ) -> ActionsSummary:
        """
        الحصول على ملخص الأنشطة حسب نوع الإجراء.
        
        Args:
            admin_id: معرف المدير (اختياري)
            limit: الحد الأقصى للنتائج
            
        Returns:
            قائمة ملخص الأنشطة
        """
        try:
            query = select(
                self.model.action,
                func.count(self.model.id).label("count"),
            ).group_by(self.model.action)

            if admin_id is not None:
                query = query.where(self.model.admin_id == admin_id)

            query = query.order_by(func.count(self.model.id).desc()).limit(limit)

            result = await self.session.execute(query)
            rows = result.all()

            return [
                {"action": row.action, "count": row.count}
                for row in rows
            ]

        except Exception as e:
            logger.exception(
                "admin_log_repo_get_actions_summary_failed",
                extra={
                    "admin_id": admin_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET RECENT ACTIVITY
    # ==============================================

    async def get_recent_activity(
        self,
        *,
        admin_id: Optional[int] = None,
        limit: int = 10,
    ) -> AdminLogList:
        """
        الحصول على أحدث الأنشطة.
        
        Args:
            admin_id: معرف المدير (اختياري)
            limit: عدد النتائج
            
        Returns:
            قائمة أحدث الأنشطة
        """
        try:
            query = select(self.model).order_by(
                self.model.timestamp.desc(),
                self.model.id.desc(),
            ).limit(limit)

            if admin_id is not None:
                query = query.where(self.model.admin_id == admin_id)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "admin_log_repo_get_recent_activity_failed",
                extra={
                    "admin_id": admin_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE LOG
    # ==============================================

    async def create_log(
        self,
        *,
        admin_id: int,
        action: str,
        resource: Optional[str] = None,
        resource_id: Optional[int] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AdminLog:
        """
        إنشاء سجل نشاط جديد.
        
        Args:
            admin_id: معرف المدير
            action: نوع الإجراء
            resource: نوع المورد (اختياري)
            resource_id: معرف المورد (اختياري)
            details: تفاصيل إضافية (اختياري)
            ip_address: عنوان IP (اختياري)
            user_agent: متصفح المدير (اختياري)
            
        Returns:
            كائن AdminLog المنشأ
        """
        logger.info(
            "admin_log_repo_create",
            extra={
                "admin_id": admin_id,
                "action": action,
                "resource": resource,
                "resource_id": resource_id,
            },
        )

        data: AdminLogData = {
            "admin_id": admin_id,
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "details": details,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.now(),
        }

        log = await self.create(data=data)

        logger.info(
            "admin_log_created_successfully",
            extra={
                "log_id": log.id,
                "admin_id": admin_id,
                "action": action,
            },
        )

        return log

    # ==============================================
    # DELETE OLD LOGS
    # ==============================================

    async def delete_old_logs(
        self,
        *,
        days: int = 30,
    ) -> int:
        """
        حذف سجلات الأنشطة الأقدم من عدد محدد من الأيام.
        
        Args:
            days: عدد الأيام (افتراضي: 30)
            
        Returns:
            عدد السجلات المحذوفة
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # جلب السجلات القديمة
            result = await self.session.execute(
                select(self.model).where(
                    self.model.timestamp < cutoff_date,
                ),
            )

            old_logs = result.scalars().all()
            count = len(old_logs)

            # حذف كل سجل
            for log in old_logs:
                await self.session.delete(log)

            await self.session.commit()

            logger.info(
                "admin_old_logs_deleted",
                extra={
                    "days": days,
                    "count": count,
                },
            )

            return count

        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "admin_log_repo_delete_old_logs_failed",
                extra={
                    "days": days,
                    "error": str(e),
                },
            )
            raise


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE ADMIN LOG (COMPATIBILITY)
# ==============================================

async def create_admin_log(
    *,
    admin_id: int,
    action: str,
    resource: Optional[str] = None,
    resource_id: Optional[int] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session: AsyncSession,
) -> int:
    """
    إنشاء سجل نشاط جديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        admin_id: معرف المدير
        action: نوع الإجراء
        resource: نوع المورد (اختياري)
        resource_id: معرف المورد (اختياري)
        details: تفاصيل إضافية (اختياري)
        ip_address: عنوان IP (اختياري)
        user_agent: متصفح المدير (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        معرف سجل النشاط
    """
    repo = AdminLogRepository(session=session)

    log = await repo.create_log(
        admin_id=admin_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return log.id


# ==============================================
# GET ADMIN LOGS (COMPATIBILITY)
# ==============================================

async def get_admin_logs(
    *,
    admin_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على سجل أنشطة مدير معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        admin_id: معرف المدير
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        قائمة سجل الأنشطة
    """
    repo = AdminLogRepository(session=session)

    logs = await repo.get_by_admin_id(
        admin_id=admin_id,
        skip=skip,
        limit=limit,
    )

    result = []

    for log in logs:
        result.append({
            "id": log.id,
            "admin_id": log.admin_id,
            "action": log.action,
            "resource": log.resource,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "timestamp": log.timestamp,
            "created_at": log.created_at,
        })

    return result


# ==============================================
# GET ADMIN LOG BY ID (COMPATIBILITY)
# ==============================================

async def get_admin_log_by_id(
    *,
    log_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على سجل نشاط بالمعرف (دالة متوافقة مع الإصدار القديم).
    
    Args:
        log_id: معرف سجل النشاط
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قاموس بيانات سجل النشاط أو None
    """
    repo = AdminLogRepository(session=session)

    log = await repo.get_by_id(id=log_id)

    if not log:
        return None

    return {
        "id": log.id,
        "admin_id": log.admin_id,
        "action": log.action,
        "resource": log.resource,
        "resource_id": log.resource_id,
        "details": log.details,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "timestamp": log.timestamp,
        "created_at": log.created_at,
    }