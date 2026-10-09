# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔐 ADMIN SESSION SERVICE
# منطق الأعمال لجلسات المديرين
# ==============================================

"""MoulAI operational module for admin session service.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.core.logger import logger
from app.core.security import generate_session_token
from app.models.admin_session import AdminSession
from app.repositories.admin.admin_sessions_repo import AdminSessionsRepository
from app.repositories.admin.admin_repo import AdminRepository
from app.schemas.admin_session import (
    AdminSessionCreate,
    AdminSessionResponse,
    AdminSessionListResponse,
    AdminSessionExtend,
)

# ==============================================
# 🧩 TYPES
# ==============================================

AdminSessionList = List[AdminSession]


# ==============================================
# 🔐 ADMIN SESSION SERVICE
# ==============================================


class AdminSessionService:
    """
    خدمة جلسات المديرين - تدير منطق الأعمال لجلسات المديرين.

    مسؤول عن:
        - إنشاء جلسات المديرين
        - التحقق من صحة الجلسات
        - تحديث آخر نشاط
        - إلغاء تنشيط الجلسات
        - تمديد صلاحية الجلسات
        - تنظيف الجلسات المنتهية

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع جلسات المديرين
        admin_repo: مستودع المديرين
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة جلسات المديرين.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = AdminSessionsRepository(session)
        self.admin_repo = AdminRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET SESSION BY TOKEN
    # ==============================================

    async def get_session_by_token(
        self,
        *,
        session_token: str,
    ) -> AdminSessionResponse:
        """
        الحصول على جلسة بواسطة رمز الجلسة.

        Args:
            session_token: رمز الجلسة

        Returns:
            AdminSessionResponse: بيانات الجلسة

        Raises:
            NotFoundError: إذا لم يتم العثور على الجلسة
        """
        logger.info(
            "admin_session_service_get_by_token",
            extra={"session_token": session_token},
        )

        session_obj = await self.repo.get_by_session_token(
            session_token=session_token,
        )

        if not session_obj:
            raise NotFoundError(
                message="الجلسة غير موجودة",
            )

        return AdminSessionResponse.model_validate(session_obj)

    # ==============================================
    # GET ACTIVE SESSION
    # ==============================================

    async def get_active_session(
        self,
        *,
        session_token: str,
    ) -> AdminSessionResponse:
        """
        الحصول على جلسة نشطة بواسطة رمز الجلسة.

        Args:
            session_token: رمز الجلسة

        Returns:
            AdminSessionResponse: بيانات الجلسة

        Raises:
            NotFoundError: إذا لم يتم العثور على الجلسة
            UnauthorizedError: إذا كانت الجلسة غير نشطة أو منتهية
        """
        logger.info(
            "admin_session_service_get_active",
            extra={"session_token": session_token},
        )

        session_obj = await self.repo.get_active_session(
            session_token=session_token,
        )

        if not session_obj:
            raise NotFoundError(
                message="الجلسة غير موجودة أو منتهية الصلاحية",
            )

        return AdminSessionResponse.model_validate(session_obj)

    # ==============================================
    # GET SESSIONS BY ADMIN
    # ==============================================

    async def get_sessions_by_admin(
        self,
        *,
        admin_id: int,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> AdminSessionListResponse:
        """
        الحصول على جلسات مدير معين.

        Args:
            admin_id: معرف المدير
            only_active: جلب الجلسات النشطة فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            AdminSessionListResponse: قائمة جلسات المدير
        """
        logger.info(
            "admin_session_service_get_by_admin",
            extra={
                "admin_id": admin_id,
                "only_active": only_active,
            },
        )

        sessions = await self.repo.get_by_admin_id(
            admin_id=admin_id,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

        total = await self.repo.count_by_admin(
            admin_id=admin_id,
            only_active=only_active,
        )

        return AdminSessionListResponse(
            items=[AdminSessionResponse.model_validate(s) for s in sessions],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET ACTIVE SESSIONS BY ADMIN
    # ==============================================

    async def get_active_sessions_by_admin(
        self,
        *,
        admin_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> AdminSessionListResponse:
        """
        الحصول على الجلسات النشطة لمدير معين.

        Args:
            admin_id: معرف المدير
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            AdminSessionListResponse: قائمة الجلسات النشطة
        """
        logger.info(
            "admin_session_service_get_active_by_admin",
            extra={
                "admin_id": admin_id,
            },
        )

        sessions = await self.repo.get_active_by_admin(
            admin_id=admin_id,
            skip=skip,
            limit=limit,
        )

        total = len(sessions)

        return AdminSessionListResponse(
            items=[AdminSessionResponse.model_validate(s) for s in sessions],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET SESSION STATUS
    # ==============================================

    async def get_session_status(
        self,
        *,
        session_token: str,
    ) -> Dict[str, Any]:
        """
        الحصول على حالة الجلسة.

        Args:
            session_token: رمز الجلسة

        Returns:
            Dict[str, Any]: حالة الجلسة

        Raises:
            NotFoundError: إذا لم يتم العثور على الجلسة
        """
        logger.info(
            "admin_session_service_get_status",
            extra={"session_token": session_token},
        )

        session_obj = await self.repo.get_by_session_token(
            session_token=session_token,
        )

        if not session_obj:
            raise NotFoundError(
                message="الجلسة غير موجودة",
            )

        now = datetime.utcnow()
        is_active = session_obj.is_active and session_obj.expires_at > now

        return {
            "is_active": is_active,
            "is_expired": session_obj.expires_at <= now,
            "expires_at": session_obj.expires_at.isoformat(),
            "last_activity": (
                session_obj.last_activity.isoformat()
                if session_obj.last_activity
                else None
            ),
            "admin_id": session_obj.admin_id,
        }

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT SESSIONS
    # ==============================================

    async def count_sessions(
        self,
        *,
        admin_id: int,
        only_active: bool = True,
    ) -> int:
        """
        حساب عدد جلسات مدير معين.

        Args:
            admin_id: معرف المدير
            only_active: حساب الجلسات النشطة فقط

        Returns:
            int: عدد الجلسات
        """
        return await self.repo.count_by_admin(
            admin_id=admin_id,
            only_active=only_active,
        )

    # ==============================================
    # GET SESSIONS STATISTICS
    # ==============================================

    async def get_statistics(
        self,
        *,
        admin_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        الحصول على إحصائيات الجلسات.

        Args:
            admin_id: معرف المدير (اختياري)

        Returns:
            Dict[str, Any]: إحصائيات الجلسات
        """
        logger.info(
            "admin_session_service_get_statistics",
            extra={"admin_id": admin_id},
        )

        total = await self.repo.count(
            admin_id=admin_id,
        )
        active = await self.repo.count(
            admin_id=admin_id,
            only_active=True,
        )
        expired = await self.repo.count_expired(
            admin_id=admin_id,
        )

        return {
            "total_sessions": total,
            "active_sessions": active,
            "expired_sessions": expired,
            "admin_id": admin_id,
        }

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE SESSION
    # ==============================================

    async def create_session(
        self,
        *,
        session_data: AdminSessionCreate,
    ) -> AdminSessionResponse:
        """
        إنشاء جلسة جديدة للمدير.

        Args:
            session_data: بيانات الجلسة

        Returns:
            AdminSessionResponse: بيانات الجلسة المنشأة

        Raises:
            NotFoundError: إذا لم يتم العثور على المدير
        """
        logger.info(
            "admin_session_service_create",
            extra={
                "admin_id": session_data.admin_id,
                "expires_at": session_data.expires_at,
            },
        )

        # التحقق من وجود المدير
        admin = await self.admin_repo.get_by_id(id=session_data.admin_id)

        if not admin:
            raise NotFoundError(
                message=f"المدير بـ ID '{session_data.admin_id}' غير موجود",
            )

        # إنشاء رمز الجلسة
        session_token = generate_session_token()

        # إنشاء الجلسة
        session_obj = await self.repo.create(
            admin_id=session_data.admin_id,
            session_token=session_token,
            expires_at=session_data.expires_at,
            ip_address=session_data.ip_address,
            user_agent=session_data.user_agent,
        )
        await self.session.commit()

        logger.info(
            "admin_session_created_successfully",
            extra={
                "session_id": session_obj.id,
                "admin_id": session_data.admin_id,
            },
        )

        return AdminSessionResponse.model_validate(session_obj)

    # ==============================================
    # UPDATE ACTIVITY
    # ==============================================

    async def update_activity(
        self,
        *,
        session_token: str,
    ) -> AdminSessionResponse:
        """
        تحديث آخر نشاط للجلسة.

        Args:
            session_token: رمز الجلسة

        Returns:
            AdminSessionResponse: بيانات الجلسة المحدثة

        Raises:
            NotFoundError: إذا لم يتم العثور على الجلسة
        """
        logger.info(
            "admin_session_service_update_activity",
            extra={"session_token": session_token},
        )

        session_obj = await self.repo.update_activity(
            session_token=session_token,
        )

        if not session_obj:
            raise NotFoundError(
                message="الجلسة غير موجودة",
            )

        await self.session.commit()

        return AdminSessionResponse.model_validate(session_obj)

    # ==============================================
    # DEACTIVATE SESSION
    # ==============================================

    async def deactivate_session(
        self,
        *,
        session_token: str,
    ) -> AdminSessionResponse:
        """
        إلغاء تنشيط الجلسة (تسجيل الخروج).

        Args:
            session_token: رمز الجلسة

        Returns:
            AdminSessionResponse: بيانات الجلسة المحدثة

        Raises:
            NotFoundError: إذا لم يتم العثور على الجلسة
        """
        logger.info(
            "admin_session_service_deactivate",
            extra={"session_token": session_token},
        )

        session_obj = await self.repo.deactivate(
            session_token=session_token,
        )

        if not session_obj:
            raise NotFoundError(
                message="الجلسة غير موجودة",
            )

        await self.session.commit()

        return AdminSessionResponse.model_validate(session_obj)

    # ==============================================
    # DEACTIVATE ALL SESSIONS
    # ==============================================

    async def deactivate_all_sessions(
        self,
        *,
        admin_id: int,
        except_session_token: Optional[str] = None,
    ) -> int:
        """
        إلغاء تنشيط جميع جلسات مدير معين.

        Args:
            admin_id: معرف المدير
            except_session_token: استثناء جلسة معينة (اختياري)

        Returns:
            int: عدد الجلسات التي تم إلغاء تنشيطها
        """
        logger.info(
            "admin_session_service_deactivate_all",
            extra={
                "admin_id": admin_id,
                "except_session_token": except_session_token,
            },
        )

        count = await self.repo.deactivate_all_sessions(
            admin_id=admin_id,
            except_session_token=except_session_token,
        )
        await self.session.commit()

        return count

    # ==============================================
    # EXTEND SESSION
    # ==============================================

    async def extend_session(
        self,
        *,
        extend_data: AdminSessionExtend,
    ) -> AdminSessionResponse:
        """
        تمديد صلاحية الجلسة.

        Args:
            extend_data: بيانات تمديد الجلسة

        Returns:
            AdminSessionResponse: بيانات الجلسة المحدثة

        Raises:
            NotFoundError: إذا لم يتم العثور على الجلسة
            ValidationError: إذا كان تاريخ الانتهاء غير صحيح
        """
        logger.info(
            "admin_session_service_extend",
            extra={
                "session_token": extend_data.session_token,
                "expires_at": extend_data.expires_at,
            },
        )

        # التحقق من أن تاريخ الانتهاء في المستقبل
        if extend_data.expires_at <= datetime.utcnow():
            raise ValidationError(
                message="تاريخ الانتهاء يجب أن يكون في المستقبل",
            )

        session_obj = await self.repo.extend_session(
            session_token=extend_data.session_token,
            expires_at=extend_data.expires_at,
        )

        if not session_obj:
            raise NotFoundError(
                message="الجلسة غير موجودة",
            )

        await self.session.commit()

        return AdminSessionResponse.model_validate(session_obj)

    # ==============================================
    # CLEANUP EXPIRED SESSIONS
    # ==============================================

    async def cleanup_expired_sessions(
        self,
        *,
        days: int = 30,
    ) -> int:
        """
        تنظيف الجلسات المنتهية.

        Args:
            days: عدد الأيام للاحتفاظ بالجلسات المنتهية (افتراضي: 30)

        Returns:
            int: عدد الجلسات التي تم تنظيفها
        """
        logger.info(
            "admin_session_service_cleanup",
            extra={"days": days},
        )

        count = await self.repo.cleanup_expired_sessions(
            days=days,
        )
        await self.session.commit()

        logger.info(
            "admin_session_cleanup_completed",
            extra={"deleted_count": count},
        )

        return count

    # ==============================================
    # VALIDATE SESSION
    # ==============================================

    async def validate_session(
        self,
        *,
        session_token: str,
    ) -> bool:
        """
        التحقق من صحة الجلسة.

        Args:
            session_token: رمز الجلسة

        Returns:
            bool: صحة الجلسة
        """
        try:
            await self.get_active_session(
                session_token=session_token,
            )
            return True
        except (NotFoundError, UnauthorizedError):
            return False


# ==============================================
# 🏢 BUSINESS LOGIC HELPERS
# ==============================================


async def create_admin_session(
    *,
    session: AsyncSession,
    admin_id: int,
    expires_in_hours: int = 24,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AdminSessionResponse:
    """
    دالة مساعدة لإنشاء جلسة مدير جديدة.

    Args:
        session: جلسة قاعدة البيانات
        admin_id: معرف المدير
        expires_in_hours: عدد ساعات صلاحية الجلسة (افتراضي: 24)
        ip_address: عنوان IP (اختياري)
        user_agent: متصفح المستخدم (اختياري)

    Returns:
        AdminSessionResponse: بيانات الجلسة المنشأة
    """
    service = AdminSessionService(session)

    expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

    session_data = AdminSessionCreate(
        admin_id=admin_id,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return await service.create_session(session_data=session_data)


# ==============================================
# LOGOUT ADMIN
# ==============================================


async def logout_admin(
    *,
    session: AsyncSession,
    session_token: str,
) -> AdminSessionResponse:
    """
    دالة مساعدة لتسجيل خروج المدير.

    Args:
        session: جلسة قاعدة البيانات
        session_token: رمز الجلسة

    Returns:
        AdminSessionResponse: بيانات الجلسة المحدثة
    """
    service = AdminSessionService(session)

    return await service.deactivate_session(
        session_token=session_token,
    )


# ==============================================
# LOGOUT ALL DEVICES
# ==============================================


async def logout_all_devices(
    *,
    session: AsyncSession,
    admin_id: int,
    except_session_token: Optional[str] = None,
) -> int:
    """
    دالة مساعدة لتسجيل الخروج من جميع الأجهزة.

    Args:
        session: جلسة قاعدة البيانات
        admin_id: معرف المدير
        except_session_token: استثناء جلسة معينة (اختياري)

    Returns:
        int: عدد الجلسات التي تم إلغاء تنشيطها
    """
    service = AdminSessionService(session)

    return await service.deactivate_all_sessions(
        admin_id=admin_id,
        except_session_token=except_session_token,
    )
