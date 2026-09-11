# ==============================================
# 🔐 ADMIN SESSIONS REPOSITORY
# عمليات قاعدة البيانات لجلسات المدير باستخدام SQLAlchemy
# ==============================================

from datetime import datetime
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
from app.models.admin_session import AdminSession
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

AdminSessionData = Dict[str, Any]
AdminSessionUpdateData = Dict[str, Any]
AdminSessionList = List[AdminSession]

# ==============================================
# 🔐 ADMIN SESSIONS REPOSITORY
# ==============================================


class AdminSessionsRepository(
    BaseRepository[
        AdminSession,
        AdminSessionData,
        AdminSessionUpdateData,
    ]
):
    """
    مستودع جلسات المدير - يوفر عمليات خاصة بجلسات المدير.
    
    مسؤول عن:
        - عمليات CRUD الأساسية لجلسات المدير
        - إدارة الجلسات النشطة والمنتهية
        - تحديث آخر نشاط للجلسة
        - تنظيف الجلسات المنتهية
    
    Attributes:
        model: نموذج AdminSession
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع جلسات المدير.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(AdminSession, session)

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
        only_active: bool = True,
    ) -> AdminSessionList:
        """
        الحصول على جلسات مدير معين.
        
        Args:
            admin_id: معرف المدير
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_active: جلب الجلسات النشطة فقط
            
        Returns:
            قائمة جلسات المدير
        """
        try:
            query = select(self.model).where(
                self.model.admin_id == admin_id,
            )

            if only_active:
                query = query.where(self.model.is_active == True)

            query = query.order_by(
                self.model.last_activity.desc(),
                self.model.created_at.desc(),
            ).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "admin_sessions_repo_get_by_admin_failed",
                extra={
                    "admin_id": admin_id,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY SESSION TOKEN
    # ==============================================

    async def get_by_session_token(
        self,
        *,
        session_token: str,
    ) -> Optional[AdminSession]:
        """
        الحصول على جلسة بواسطة رمز الجلسة.
        
        Args:
            session_token: رمز الجلسة
            
        Returns:
            كائن AdminSession أو None
        """
        try:
            result = await self.session.execute(
                select(self.model)
                .where(self.model.session_token == session_token)
                .limit(1),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "admin_sessions_repo_get_by_token_failed",
                extra={
                    "session_token": session_token,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET ACTIVE SESSION
    # ==============================================

    async def get_active_session(
        self,
        *,
        session_token: str,
    ) -> Optional[AdminSession]:
        """
        الحصول على جلسة نشطة بواسطة رمز الجلسة.
        
        Args:
            session_token: رمز الجلسة
            
        Returns:
            كائن AdminSession أو None
        """
        try:
            result = await self.session.execute(
                select(self.model)
                .where(
                    and_(
                        self.model.session_token == session_token,
                        self.model.is_active == True,
                        self.model.expires_at >= datetime.now(),
                    ),
                )
                .limit(1),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "admin_sessions_repo_get_active_session_failed",
                extra={
                    "session_token": session_token,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET ACTIVE BY ADMIN
    # ==============================================

    async def get_active_by_admin(
        self,
        *,
        admin_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> AdminSessionList:
        """
        الحصول على الجلسات النشطة لمدير معين.
        
        Args:
            admin_id: معرف المدير
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة الجلسات النشطة
        """
        try:
            query = (
                select(self.model)
                .where(
                    and_(
                        self.model.admin_id == admin_id,
                        self.model.is_active == True,
                        self.model.expires_at >= datetime.now(),
                    ),
                )
                .order_by(
                    self.model.last_activity.desc(),
                    self.model.created_at.desc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "admin_sessions_repo_get_active_by_admin_failed",
                extra={
                    "admin_id": admin_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET EXPIRED SESSIONS
    # ==============================================

    async def get_expired_sessions(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> AdminSessionList:
        """
        الحصول على الجلسات المنتهية.
        
        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة الجلسات المنتهية
        """
        try:
            query = (
                select(self.model)
                .where(
                    or_(
                        self.model.is_active == False,
                        self.model.expires_at < datetime.now(),
                    ),
                )
                .order_by(self.model.expires_at.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "admin_sessions_repo_get_expired_failed",
                extra={"error": str(e)},
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
    ) -> AdminSessionList:
        """
        البحث عن جلسات المدير.
        
        Args:
            query: نص البحث (IP أو User Agent)
            admin_id: معرف المدير (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة جلسات المدير
        """
        try:
            conditions = [
                or_(
                    self.model.ip_address.ilike(f"%{query}%"),
                    self.model.user_agent.ilike(f"%{query}%"),
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
                    self.model.last_activity.desc(),
                    self.model.created_at.desc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "admin_sessions_repo_search_failed",
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
        only_active: bool = True,
    ) -> int:
        """
        حساب عدد جلسات مدير معين.
        
        Args:
            admin_id: معرف المدير
            only_active: حساب الجلسات النشطة فقط
            
        Returns:
            عدد الجلسات
        """
        filters = {"admin_id": admin_id}

        if only_active:
            filters["is_active"] = True

        return await self.count(filters=filters)

    # ==============================================
    # COUNT ACTIVE
    # ==============================================

    async def count_active(
        self,
    ) -> int:
        """
        حساب عدد الجلسات النشطة.
        
        Returns:
            عدد الجلسات النشطة
        """
        return await self.count(filters={"is_active": True})

    # ==============================================
    # COUNT EXPIRED
    # ==============================================

    async def count_expired(
        self,
    ) -> int:
        """
        حساب عدد الجلسات المنتهية.
        
        Returns:
            عدد الجلسات المنتهية
        """
        return await self.count(filters={"is_active": False})

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE SESSION
    # ==============================================

    async def create_session(
        self,
        *,
        admin_id: int,
        session_token: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AdminSession:
        """
        إنشاء جلسة جديدة للمدير.
        
        Args:
            admin_id: معرف المدير
            session_token: رمز الجلسة
            expires_at: تاريخ انتهاء الجلسة
            ip_address: عنوان IP (اختياري)
            user_agent: متصفح المدير (اختياري)
            
        Returns:
            كائن AdminSession المنشأ
        """
        logger.info(
            "admin_sessions_repo_create",
            extra={
                "admin_id": admin_id,
                "expires_at": expires_at,
            },
        )

        data: AdminSessionData = {
            "admin_id": admin_id,
            "session_token": session_token,
            "expires_at": expires_at,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "is_active": True,
            "last_activity": datetime.now(),
        }

        session_obj = await self.create(data=data)

        logger.info(
            "admin_session_created_successfully",
            extra={
                "session_id": session_obj.id,
                "admin_id": admin_id,
            },
        )

        return session_obj

    # ==============================================
    # UPDATE ACTIVITY
    # ==============================================

    async def update_activity(
        self,
        *,
        session_token: str,
    ) -> Optional[AdminSession]:
        """
        تحديث آخر نشاط للجلسة.
        
        Args:
            session_token: رمز الجلسة
            
        Returns:
            كائن AdminSession المحدث أو None
        """
        logger.info(
            "admin_sessions_repo_update_activity",
            extra={"session_token": session_token},
        )

        session_obj = await self.get_by_session_token(
            session_token=session_token,
        )

        if not session_obj:
            logger.warning(
                "admin_session_not_found_for_activity",
                extra={"session_token": session_token},
            )
            return None

        session_obj.last_activity = datetime.now()
        await self.session.commit()
        await self.session.refresh(session_obj)

        logger.info(
            "admin_session_activity_updated",
            extra={
                "session_id": session_obj.id,
                "session_token": session_token,
            },
        )

        return session_obj

    # ==============================================
    # DEACTIVATE SESSION
    # ==============================================

    async def deactivate_session(
        self,
        *,
        session_token: str,
    ) -> Optional[AdminSession]:
        """
        إلغاء تنشيط الجلسة (تسجيل الخروج).
        
        Args:
            session_token: رمز الجلسة
            
        Returns:
            كائن AdminSession المحدث أو None
        """
        logger.info(
            "admin_sessions_repo_deactivate",
            extra={"session_token": session_token},
        )

        session_obj = await self.get_by_session_token(
            session_token=session_token,
        )

        if not session_obj:
            logger.warning(
                "admin_session_not_found_for_deactivate",
                extra={"session_token": session_token},
            )
            return None

        session_obj.is_active = False
        await self.session.commit()
        await self.session.refresh(session_obj)

        logger.info(
            "admin_session_deactivated_successfully",
            extra={
                "session_id": session_obj.id,
                "session_token": session_token,
            },
        )

        return session_obj

    # ==============================================
    # DEACTIVATE ALL SESSIONS
    # ==============================================

    async def deactivate_all_sessions(
        self,
        *,
        admin_id: int,
    ) -> int:
        """
        إلغاء تنشيط جميع جلسات مدير معين.
        
        Args:
            admin_id: معرف المدير
            
        Returns:
            عدد الجلسات التي تم إلغاء تنشيطها
        """
        logger.info(
            "admin_sessions_repo_deactivate_all",
            extra={"admin_id": admin_id},
        )

        sessions = await self.get_by_admin_id(
            admin_id=admin_id,
            only_active=True,
        )

        count = 0

        for session_obj in sessions:
            session_obj.is_active = False
            count += 1

        await self.session.commit()

        logger.info(
            "admin_all_sessions_deactivated",
            extra={
                "admin_id": admin_id,
                "count": count,
            },
        )

        return count

    # ==============================================
    # EXTEND SESSION
    # ==============================================

    async def extend_session(
        self,
        *,
        session_token: str,
        expires_at: datetime,
    ) -> Optional[AdminSession]:
        """
        تمديد صلاحية الجلسة.
        
        Args:
            session_token: رمز الجلسة
            expires_at: تاريخ الانتهاء الجديد
            
        Returns:
            كائن AdminSession المحدث أو None
        """
        logger.info(
            "admin_sessions_repo_extend",
            extra={
                "session_token": session_token,
                "expires_at": expires_at,
            },
        )

        session_obj = await self.get_by_session_token(
            session_token=session_token,
        )

        if not session_obj:
            logger.warning(
                "admin_session_not_found_for_extend",
                extra={"session_token": session_token},
            )
            return None

        session_obj.expires_at = expires_at
        session_obj.is_active = True
        await self.session.commit()
        await self.session.refresh(session_obj)

        logger.info(
            "admin_session_extended_successfully",
            extra={
                "session_id": session_obj.id,
                "session_token": session_token,
                "expires_at": expires_at,
            },
        )

        return session_obj

    # ==============================================
    # CLEANUP EXPIRED SESSIONS
    # ==============================================

    async def cleanup_expired_sessions(
        self,
    ) -> int:
        """
        تنظيف الجلسات المنتهية (تعيين is_active = False).
        
        Returns:
            عدد الجلسات التي تم تنظيفها
        """
        logger.info("admin_sessions_repo_cleanup")

        expired_sessions = await self.get_expired_sessions()

        count = 0

        for session_obj in expired_sessions:
            session_obj.is_active = False
            count += 1

        await self.session.commit()

        logger.info(
            "admin_expired_sessions_cleaned",
            extra={"count": count},
        )

        return count


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE ADMIN SESSION (COMPATIBILITY)
# ==============================================

async def create_admin_session(
    *,
    admin_id: int,
    session_token: str,
    expires_at: datetime,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session: AsyncSession,
) -> int:
    """
    إنشاء جلسة جديدة للمدير (دالة متوافقة مع الإصدار القديم).
    
    Args:
        admin_id: معرف المدير
        session_token: رمز الجلسة
        expires_at: تاريخ انتهاء الجلسة
        ip_address: عنوان IP (اختياري)
        user_agent: متصفح المدير (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        معرف الجلسة
    """
    repo = AdminSessionsRepository(session=session)

    session_obj = await repo.create_session(
        admin_id=admin_id,
        session_token=session_token,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return session_obj.id


# ==============================================
# GET ADMIN SESSION (COMPATIBILITY)
# ==============================================

async def get_admin_session(
    *,
    session_token: str,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على جلسة بواسطة رمز الجلسة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        session_token: رمز الجلسة
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قاموس بيانات الجلسة أو None
    """
    repo = AdminSessionsRepository(session=session)

    session_obj = await repo.get_by_session_token(
        session_token=session_token,
    )

    if not session_obj:
        return None

    return {
        "id": session_obj.id,
        "admin_id": session_obj.admin_id,
        "session_token": session_obj.session_token,
        "ip_address": session_obj.ip_address,
        "user_agent": session_obj.user_agent,
        "expires_at": session_obj.expires_at,
        "is_active": session_obj.is_active,
        "last_activity": session_obj.last_activity,
        "created_at": session_obj.created_at,
    }


# ==============================================
# GET ADMIN ACTIVE SESSION (COMPATIBILITY)
# ==============================================

async def get_admin_active_session(
    *,
    session_token: str,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على جلسة نشطة بواسطة رمز الجلسة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        session_token: رمز الجلسة
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قاموس بيانات الجلسة أو None
    """
    repo = AdminSessionsRepository(session=session)

    session_obj = await repo.get_active_session(
        session_token=session_token,
    )

    if not session_obj:
        return None

    return {
        "id": session_obj.id,
        "admin_id": session_obj.admin_id,
        "session_token": session_obj.session_token,
        "ip_address": session_obj.ip_address,
        "user_agent": session_obj.user_agent,
        "expires_at": session_obj.expires_at,
        "is_active": session_obj.is_active,
        "last_activity": session_obj.last_activity,
        "created_at": session_obj.created_at,
    }


# ==============================================
# DEACTIVATE ADMIN SESSION (COMPATIBILITY)
# ==============================================

async def deactivate_admin_session(
    *,
    session_token: str,
    session: AsyncSession,
) -> None:
    """
    إلغاء تنشيط الجلسة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        session_token: رمز الجلسة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = AdminSessionsRepository(session=session)

    await repo.deactivate_session(
        session_token=session_token,
    )

    logger.info(
        "admin_session_deactivated",
        extra={"session_token": session_token},
    )


# ==============================================
# GET ADMIN SESSIONS (COMPATIBILITY)
# ==============================================

async def get_admin_sessions(
    *,
    admin_id: int,
    session: AsyncSession,
    only_active: bool = True,
) -> List[Dict[str, Any]]:
    """
    الحصول على جلسات مدير معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        admin_id: معرف المدير
        session: جلسة قاعدة البيانات غير المتزامنة
        only_active: جلب الجلسات النشطة فقط
        
    Returns:
        قائمة جلسات المدير
    """
    repo = AdminSessionsRepository(session=session)

    sessions = await repo.get_by_admin_id(
        admin_id=admin_id,
        only_active=only_active,
    )

    result = []

    for s in sessions:
        result.append({
            "id": s.id,
            "admin_id": s.admin_id,
            "session_token": s.session_token,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "expires_at": s.expires_at,
            "is_active": s.is_active,
            "last_activity": s.last_activity,
            "created_at": s.created_at,
        })

    return result