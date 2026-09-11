# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 📋 ADMIN LOG SERVICE
# منطق الأعمال لسجل أنشطة المديرين
# ==============================================

from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logger import logger
from app.repositories.admin.admin_log_repo import AdminLogRepository
from app.schemas.admin_log import (
    AdminLogCreate,
    AdminLogResponse,
    AdminLogListResponse,
    AdminLogFilter,
)


# ==============================================
# 🧩 TYPES
# ==============================================

ActionsSummary = List[Dict[str, Any]]


# ==============================================
# 📋 ADMIN LOG SERVICE
# ==============================================

class AdminLogService:
    """
    خدمة سجل أنشطة المديرين - تدير منطق الأعمال لسجل الأنشطة.
    
    مسؤول عن:
        - إنشاء سجلات الأنشطة
        - قراءة سجلات الأنشطة
        - البحث والتصفية
        - إحصائيات الأنشطة
        - تنظيف السجلات القديمة
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع سجل الأنشطة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة سجل أنشطة المديرين.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = AdminLogRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET LOG BY ID
    # ==============================================

    async def get_log_by_id(
        self,
        *,
        log_id: int,
    ) -> AdminLogResponse:
        """
        الحصول على سجل نشاط بالمعرف.
        
        Args:
            log_id: معرف سجل النشاط
            
        Returns:
            AdminLogResponse: بيانات سجل النشاط
            
        Raises:
            NotFoundError: إذا لم يتم العثور على السجل
        """
        logger.info(
            "admin_log_service_get_by_id",
            extra={"log_id": log_id},
        )

        log = await self.repo.get_by_id(id=log_id)

        if not log:
            raise NotFoundError(
                message=f"سجل النشاط بـ ID '{log_id}' غير موجود",
            )

        return AdminLogResponse.model_validate(log)

    # ==============================================
    # GET LOGS BY ADMIN
    # ==============================================

    async def get_logs_by_admin(
        self,
        *,
        admin_id: int,
        filters: Optional[AdminLogFilter] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> AdminLogListResponse:
        """
        الحصول على سجل أنشطة مدير معين.
        
        Args:
            admin_id: معرف المدير
            filters: معايير التصفية (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            AdminLogListResponse: قائمة سجل الأنشطة
        """
        logger.info(
            "admin_log_service_get_by_admin",
            extra={
                "admin_id": admin_id,
                "skip": skip,
                "limit": limit,
            },
        )

        action = filters.action if filters else None
        resource = filters.resource if filters else None

        logs = await self.repo.get_by_admin_id(
            admin_id=admin_id,
            skip=skip,
            limit=limit,
            action=action,
            resource=resource,
        )

        total = await self.repo.count_by_admin(
            admin_id=admin_id,
            action=action,
        )

        return AdminLogListResponse(
            items=[AdminLogResponse.model_validate(log) for log in logs],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET LOGS BY ACTION
    # ==============================================

    async def get_logs_by_action(
        self,
        *,
        action: str,
        admin_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> AdminLogListResponse:
        """
        الحصول على سجل الأنشطة حسب نوع الإجراء.
        
        Args:
            action: نوع الإجراء
            admin_id: معرف المدير (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            AdminLogListResponse: قائمة سجل الأنشطة
        """
        logger.info(
            "admin_log_service_get_by_action",
            extra={
                "action": action,
                "admin_id": admin_id,
            },
        )

        logs = await self.repo.get_by_action(
            action=action,
            skip=skip,
            limit=limit,
            admin_id=admin_id,
        )

        total = await self.repo.count_by_action(action=action)

        return AdminLogListResponse(
            items=[AdminLogResponse.model_validate(log) for log in logs],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # SEARCH LOGS
    # ==============================================

    async def search_logs(
        self,
        *,
        query: str,
        admin_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> AdminLogListResponse:
        """
        البحث في سجل الأنشطة.
        
        Args:
            query: نص البحث
            admin_id: معرف المدير (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            AdminLogListResponse: قائمة سجل الأنشطة
        """
        logger.info(
            "admin_log_service_search",
            extra={
                "query": query,
                "admin_id": admin_id,
            },
        )

        logs = await self.repo.search(
            query=query,
            admin_id=admin_id,
            skip=skip,
            limit=limit,
        )

        total = len(logs)

        return AdminLogListResponse(
            items=[AdminLogResponse.model_validate(log) for log in logs],
            total=total,
            skip=skip,
            limit=limit,
        )

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
            ActionsSummary: قائمة ملخص الأنشطة
        """
        logger.info(
            "admin_log_service_get_actions_summary",
            extra={
                "admin_id": admin_id,
                "limit": limit,
            },
        )

        return await self.repo.get_actions_summary(
            admin_id=admin_id,
            limit=limit,
        )

    # ==============================================
    # GET RECENT ACTIVITY
    # ==============================================

    async def get_recent_activity(
        self,
        *,
        admin_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[AdminLogResponse]:
        """
        الحصول على أحدث الأنشطة.
        
        Args:
            admin_id: معرف المدير (اختياري)
            limit: عدد النتائج
            
        Returns:
            List[AdminLogResponse]: قائمة أحدث الأنشطة
        """
        logger.info(
            "admin_log_service_get_recent_activity",
            extra={
                "admin_id": admin_id,
                "limit": limit,
            },
        )

        logs = await self.repo.get_recent_activity(
            admin_id=admin_id,
            limit=limit,
        )

        return [AdminLogResponse.model_validate(log) for log in logs]

    # ==============================================
    # GET LOGS BY DATE RANGE
    # ==============================================

    async def get_logs_by_date_range(
        self,
        *,
        start_date: datetime,
        end_date: datetime,
        admin_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> AdminLogListResponse:
        """
        الحصول على سجل الأنشطة في نطاق زمني محدد.
        
        Args:
            start_date: تاريخ البداية
            end_date: تاريخ النهاية
            admin_id: معرف المدير (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            AdminLogListResponse: قائمة سجل الأنشطة
        """
        logger.info(
            "admin_log_service_get_by_date_range",
            extra={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "admin_id": admin_id,
            },
        )

        logs = await self.repo.get_by_date_range(
            start_date=start_date,
            end_date=end_date,
            admin_id=admin_id,
            skip=skip,
            limit=limit,
        )

        total = len(logs)

        return AdminLogListResponse(
            items=[AdminLogResponse.model_validate(log) for log in logs],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE LOG
    # ==============================================

    async def create_log(
        self,
        *,
        log_data: AdminLogCreate,
    ) -> AdminLogResponse:
        """
        إنشاء سجل نشاط جديد.
        
        Args:
            log_data: بيانات سجل النشاط
            
        Returns:
            AdminLogResponse: سجل النشاط المنشأ
        """
        logger.info(
            "admin_log_service_create",
            extra={
                "admin_id": log_data.admin_id,
                "action": log_data.action,
            },
        )

        log = await self.repo.create(
            log_data=log_data,
        )
        await self.session.commit()

        logger.info(
            "admin_log_created_successfully",
            extra={
                "log_id": log.id,
                "admin_id": log_data.admin_id,
                "action": log_data.action,
            },
        )

        return AdminLogResponse.model_validate(log)

    # ==============================================
    # CREATE LOG WITH DETAILS
    # ==============================================

    async def create_log_with_details(
        self,
        *,
        admin_id: int,
        action: str,
        resource: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AdminLogResponse:
        """
        إنشاء سجل نشاط جديد مع تفاصيل إضافية.
        
        Args:
            admin_id: معرف المدير
            action: نوع الإجراء
            resource: نوع المورد
            resource_id: معرف المورد (اختياري)
            details: تفاصيل إضافية (اختياري)
            ip_address: عنوان IP (اختياري)
            user_agent: متصفح المستخدم (اختياري)
            
        Returns:
            AdminLogResponse: سجل النشاط المنشأ
        """
        logger.info(
            "admin_log_service_create_with_details",
            extra={
                "admin_id": admin_id,
                "action": action,
                "resource": resource,
                "resource_id": resource_id,
            },
        )

        log_data = AdminLogCreate(
            admin_id=admin_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        log = await self.repo.create(
            log_data=log_data,
        )
        await self.session.commit()

        logger.info(
            "admin_log_created_successfully",
            extra={
                "log_id": log.id,
                "admin_id": admin_id,
                "action": action,
            },
        )

        return AdminLogResponse.model_validate(log)

    # ==========================================
    # 🔄 MAINTENANCE
    # ==========================================

    # ==============================================
    # CLEANUP OLD LOGS
    # ==============================================

    async def cleanup_old_logs(
        self,
        *,
        days: int = 90,
    ) -> int:
        """
        تنظيف السجلات القديمة.
        
        Args:
            days: عدد الأيام للاحتفاظ بالسجلات (افتراضي: 90)
            
        Returns:
            int: عدد السجلات المحذوفة
        """
        logger.info(
            "admin_log_service_cleanup_old_logs",
            extra={"days": days},
        )

        cutoff_date = datetime.utcnow() - datetime.timedelta(days=days)
        deleted_count = await self.repo.delete_old_logs(cutoff_date=cutoff_date)
        await self.session.commit()

        logger.info(
            "admin_log_service_cleanup_completed",
            extra={"deleted_count": deleted_count},
        )

        return deleted_count

    # ==============================================
    # GET STATISTICS
    # ==============================================

    async def get_statistics(
        self,
        *,
        admin_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        الحصول على إحصائيات الأنشطة.
        
        Args:
            admin_id: معرف المدير (اختياري)
            
        Returns:
            Dict[str, Any]: إحصائيات الأنشطة
        """
        logger.info(
            "admin_log_service_get_statistics",
            extra={"admin_id": admin_id},
        )

        total_count = await self.repo.count(admin_id=admin_id)
        actions_summary = await self.repo.get_actions_summary(admin_id=admin_id)

        return {
            "total_actions": total_count,
            "actions_summary": actions_summary,
            "admin_id": admin_id,
        }


# ==============================================
# 🏢 BUSINESS LOGIC HELPERS
# ==============================================

async def log_admin_action(
    *,
    session: AsyncSession,
    admin_id: int,
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AdminLogResponse:
    """
    دالة مساعدة لتسجيل إجراءات المديرين - تستخدم في طبقة الأعمال.
    
    Args:
        session: جلسة قاعدة البيانات
        admin_id: معرف المدير
        action: نوع الإجراء
        resource: نوع المورد
        resource_id: معرف المورد (اختياري)
        details: تفاصيل إضافية (اختياري)
        ip_address: عنوان IP (اختياري)
        user_agent: متصفح المستخدم (اختياري)
        
    Returns:
        AdminLogResponse: سجل النشاط المنشأ
    """
    service = AdminLogService(session)
    
    return await service.create_log_with_details(
        admin_id=admin_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )


# ==============================================
# 🏢 AUDIT HELPERS
# ==============================================

async def audit_resource_access(
    *,
    session: AsyncSession,
    admin_id: int,
    resource: str,
    resource_id: str,
    action: str = "view",
) -> None:
    """
    تسجيل وصول المدير إلى مورد معين لأغراض التدقيق.
    
    Args:
        session: جلسة قاعدة البيانات
        admin_id: معرف المدير
        resource: نوع المورد
        resource_id: معرف المورد
        action: نوع الإجراء (افتراضي: view)
    """
    await log_admin_action(
        session=session,
        admin_id=admin_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        details={"audit": True},
    )