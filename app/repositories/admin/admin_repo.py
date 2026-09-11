# ==============================================
# 👑 ADMIN REPOSITORY
# عمليات قاعدة البيانات للمديرين باستخدام SQLAlchemy
# ==============================================

from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.admin import Admin
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

AdminData = Dict[str, Any]
AdminUpdateData = Dict[str, Any]
AdminList = List[Admin]
AdminDictList = List[Dict[str, Any]]

# ==============================================
# 👑 ADMIN REPOSITORY
# ==============================================


class AdminRepository(
    BaseRepository[
        Admin,
        AdminData,
        AdminUpdateData,
    ]
):
    """
    مستودع المديرين - يوفر عمليات خاصة بجدول المديرين.
    
    مسؤول عن:
        - عمليات CRUD الأساسية للمديرين
        - البحث عن المديرين بواسطة chat_id و username
        - التحقق من وجود المديرين
        - إدارة حالة المدير (نشط/غير نشط)
        - تحديث دور المدير
    
    Attributes:
        model: نموذج Admin
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع المديرين.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Admin, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY CHAT ID
    # ==============================================

    async def get_by_chat_id(
        self,
        *,
        chat_id: int,
        only_active: bool = True,
    ) -> Optional[Admin]:
        """
        الحصول على مدير بواسطة معرف الدردشة.
        
        Args:
            chat_id: معرف الدردشة في Telegram
            only_active: جلب المدير النشط فقط
            
        Returns:
            كائن Admin أو None
        """
        try:
            query = select(self.model).where(
                self.model.chat_id == chat_id,
            )

            if only_active:
                query = query.where(self.model.is_active == True)

            query = query.limit(1)

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "admin_repo_get_by_chat_id_failed",
                extra={
                    "chat_id": chat_id,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY USERNAME
    # ==============================================

    async def get_by_username(
        self,
        *,
        username: str,
        only_active: bool = True,
    ) -> Optional[Admin]:
        """
        الحصول على مدير بواسطة اسم المستخدم.
        
        Args:
            username: اسم المستخدم
            only_active: جلب المدير النشط فقط
            
        Returns:
            كائن Admin أو None
        """
        try:
            query = select(self.model).where(
                self.model.username == username,
            )

            if only_active:
                query = query.where(self.model.is_active == True)

            query = query.limit(1)

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "admin_repo_get_by_username_failed",
                extra={
                    "username": username,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # CHECK IF ADMIN EXISTS
    # ==============================================

    async def exists(
        self,
        *,
        chat_id: int,
        only_active: bool = True,
    ) -> bool:
        """
        التحقق من وجود مدير.
        
        Args:
            chat_id: معرف الدردشة في Telegram
            only_active: التحقق من المدير النشط فقط
            
        Returns:
            True إذا كان المدير موجوداً، False وإلا
        """
        try:
            query = select(self.model.id).where(
                self.model.chat_id == chat_id,
            )

            if only_active:
                query = query.where(self.model.is_active == True)

            query = query.limit(1)

            result = await self.session.execute(query)

            return result.scalar_one_or_none() is not None

        except Exception as e:
            logger.exception(
                "admin_repo_exists_failed",
                extra={
                    "chat_id": chat_id,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET ALL ADMINS
    # ==============================================

    async def get_all(
        self,
        *,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = "id",
        order_desc: bool = False,
    ) -> AdminList:
        """
        الحصول على جميع المديرين.
        
        Args:
            only_active: جلب المديرين النشطين فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            order_by: حقل الترتيب
            order_desc: ترتيب تنازلي
            
        Returns:
            قائمة المديرين
        """
        try:
            query = select(self.model)

            if only_active:
                query = query.where(self.model.is_active == True)

            # تطبيق الترتيب
            if order_by:
                column = getattr(self.model, order_by, self.model.id)
                if order_desc:
                    query = query.order_by(column.desc())
                else:
                    query = query.order_by(column.asc())

            query = query.offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "admin_repo_get_all_failed",
                extra={
                    "only_active": only_active,
                    "skip": skip,
                    "limit": limit,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY ROLE
    # ==============================================

    async def get_by_role(
        self,
        *,
        role: str,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> AdminList:
        """
        الحصول على المديرين بواسطة الدور.
        
        Args:
            role: دور المدير (admin, super_admin, manager)
            only_active: جلب المديرين النشطين فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة المديرين
        """
        try:
            query = select(self.model).where(
                self.model.role == role,
            )

            if only_active:
                query = query.where(self.model.is_active == True)

            query = query.order_by(
                self.model.id.asc(),
            ).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "admin_repo_get_by_role_failed",
                extra={
                    "role": role,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # SEARCH ADMINS
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> AdminList:
        """
        البحث عن المديرين.
        
        Args:
            query: نص البحث (username أو full_name)
            only_active: جلب المديرين النشطين فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة المديرين
        """
        try:
            conditions = [
                or_(
                    self.model.username.ilike(f"%{query}%"),
                    self.model.full_name.ilike(f"%{query}%"),
                ),
            ]

            if only_active:
                conditions.append(
                    self.model.is_active == True,
                )

            stmt = (
                select(self.model)
                .where(*conditions)
                .order_by(
                    self.model.full_name.asc(),
                    self.model.id.asc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "admin_repo_search_failed",
                extra={
                    "query": query,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY ROLE
    # ==============================================

    async def count_by_role(
        self,
        *,
        role: str,
        only_active: bool = True,
    ) -> int:
        """
        حساب عدد المديرين حسب الدور.
        
        Args:
            role: دور المدير
            only_active: حساب المديرين النشطين فقط
            
        Returns:
            عدد المديرين
        """
        filters = {"role": role}

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
        حساب عدد المديرين النشطين.
        
        Returns:
            عدد المديرين النشطين
        """
        return await self.count(filters={"is_active": True})

    # ==============================================
    # COUNT INACTIVE
    # ==============================================

    async def count_inactive(
        self,
    ) -> int:
        """
        حساب عدد المديرين غير النشطين.
        
        Returns:
            عدد المديرين غير النشطين
        """
        return await self.count(filters={"is_active": False})

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE ADMIN
    # ==============================================

    async def create_admin(
        self,
        *,
        chat_id: int,
        username: str,
        full_name: str,
        role: str = "admin",
        password_hash: Optional[str] = None,
        is_active: bool = True,
    ) -> Admin:
        """
        إنشاء مدير جديد.
        
        Args:
            chat_id: معرف الدردشة في Telegram
            username: اسم المستخدم
            full_name: الاسم الكامل
            role: دور المدير (admin, super_admin, manager)
            password_hash: هاش كلمة المرور (اختياري)
            is_active: حالة المدير
            
        Returns:
            كائن Admin المنشأ
        """
        logger.info(
            "admin_repo_create",
            extra={
                "chat_id": chat_id,
                "username": username,
                "role": role,
            },
        )

        data: AdminData = {
            "chat_id": chat_id,
            "username": username,
            "full_name": full_name,
            "role": role,
            "password_hash": password_hash,
            "is_active": is_active,
        }

        admin_obj = await self.create(data=data)

        logger.info(
            "admin_created_successfully",
            extra={
                "admin_id": admin_obj.id,
                "chat_id": chat_id,
                "username": username,
            },
        )

        return admin_obj

    # ==============================================
    # UPDATE ADMIN
    # ==============================================

    async def update_admin(
        self,
        *,
        admin_id: int,
        **updates,
    ) -> Optional[Admin]:
        """
        تحديث بيانات المدير.
        
        Args:
            admin_id: معرف المدير
            **updates: الحقول المراد تحديثها
            
        Returns:
            كائن Admin المحدث أو None
        """
        logger.info(
            "admin_repo_update",
            extra={
                "admin_id": admin_id,
                "updates": updates,
            },
        )

        # إزالة الحقول الفارغة
        clean_updates: AdminUpdateData = {
            k: v for k, v in updates.items()
            if v is not None
        }

        if not clean_updates:
            logger.warning(
                "admin_repo_update_no_fields",
                extra={"admin_id": admin_id},
            )
            return await self.get_by_id(id=admin_id)

        # تحديث updated_at تلقائياً
        clean_updates["updated_at"] = datetime.now()

        admin_obj = await self.update(
            id=admin_id,
            data=clean_updates,
        )

        if admin_obj:
            logger.info(
                "admin_updated_successfully",
                extra={
                    "admin_id": admin_id,
                    "updated_fields": list(clean_updates.keys()),
                },
            )

        return admin_obj

    # ==============================================
    # UPDATE ROLE
    # ==============================================

    async def update_role(
        self,
        *,
        admin_id: int,
        role: str,
    ) -> Optional[Admin]:
        """
        تحديث دور المدير.
        
        Args:
            admin_id: معرف المدير
            role: الدور الجديد
            
        Returns:
            كائن Admin المحدث أو None
        """
        logger.info(
            "admin_repo_update_role",
            extra={
                "admin_id": admin_id,
                "role": role,
            },
        )

        return await self.update_admin(
            admin_id=admin_id,
            role=role,
        )

    # ==============================================
    # TOGGLE ACTIVE STATUS
    # ==============================================

    async def toggle_active(
        self,
        *,
        admin_id: int,
    ) -> Optional[Admin]:
        """
        تبديل حالة المدير (نشط/غير نشط).
        
        Args:
            admin_id: معرف المدير
            
        Returns:
            كائن Admin المحدث أو None
        """
        logger.info(
            "admin_repo_toggle_active",
            extra={"admin_id": admin_id},
        )

        admin_obj = await self.get_by_id(id=admin_id)

        if not admin_obj:
            logger.warning(
                "admin_not_found_for_toggle",
                extra={"admin_id": admin_id},
            )
            return None

        new_status = not admin_obj.is_active

        updated_obj = await self.update_admin(
            admin_id=admin_id,
            is_active=new_status,
        )

        logger.info(
            "admin_toggle_active_successfully",
            extra={
                "admin_id": admin_id,
                "is_active": new_status,
            },
        )

        return updated_obj

    # ==============================================
    # ACTIVATE ADMIN
    # ==============================================

    async def activate(
        self,
        *,
        admin_id: int,
    ) -> Optional[Admin]:
        """
        تنشيط المدير.
        
        Args:
            admin_id: معرف المدير
            
        Returns:
            كائن Admin المحدث أو None
        """
        logger.info(
            "admin_repo_activate",
            extra={"admin_id": admin_id},
        )

        return await self.update_admin(
            admin_id=admin_id,
            is_active=True,
        )

    # ==============================================
    # DEACTIVATE ADMIN
    # ==============================================

    async def deactivate(
        self,
        *,
        admin_id: int,
    ) -> Optional[Admin]:
        """
        إلغاء تنشيط المدير.
        
        Args:
            admin_id: معرف المدير
            
        Returns:
            كائن Admin المحدث أو None
        """
        logger.info(
            "admin_repo_deactivate",
            extra={"admin_id": admin_id},
        )

        return await self.update_admin(
            admin_id=admin_id,
            is_active=False,
        )

    # ==============================================
    # UPDATE PASSWORD HASH
    # ==============================================

    async def update_password_hash(
        self,
        *,
        admin_id: int,
        password_hash: str,
    ) -> Optional[Admin]:
        """
        تحديث هاش كلمة المرور.
        
        Args:
            admin_id: معرف المدير
            password_hash: هاش كلمة المرور الجديد
            
        Returns:
            كائن Admin المحدث أو None
        """
        logger.info(
            "admin_repo_update_password_hash",
            extra={"admin_id": admin_id},
        )

        return await self.update_admin(
            admin_id=admin_id,
            password_hash=password_hash,
        )

    # ==============================================
    # DELETE ADMIN (SOFT DELETE)
    # ==============================================

    async def delete_admin(
        self,
        *,
        admin_id: int,
    ) -> bool:
        """
        حذف المدير (تعيين is_active = False).
        
        Args:
            admin_id: معرف المدير
            
        Returns:
            True إذا تم الحذف، False وإلا
        """
        logger.info(
            "admin_repo_delete",
            extra={"admin_id": admin_id},
        )

        admin_obj = await self.deactivate(admin_id=admin_id)

        if admin_obj:
            logger.info(
                "admin_deleted_successfully",
                extra={"admin_id": admin_id},
            )
            return True

        logger.warning(
            "admin_delete_failed",
            extra={"admin_id": admin_id},
        )
        return False

    # ==============================================
    # DELETE ADMIN PERMANENTLY
    # ==============================================

    async def delete_permanently(
        self,
        *,
        admin_id: int,
    ) -> bool:
        """
        حذف المدير نهائياً من قاعدة البيانات.
        
        Args:
            admin_id: معرف المدير
            
        Returns:
            True إذا تم الحذف، False وإلا
        """
        logger.info(
            "admin_repo_delete_permanently",
            extra={"admin_id": admin_id},
        )

        try:
            result = await self.delete(id=admin_id)

            if result:
                logger.info(
                    "admin_deleted_permanently",
                    extra={"admin_id": admin_id},
                )
                return True

            return False

        except Exception as e:
            logger.exception(
                "admin_repo_delete_permanently_failed",
                extra={
                    "admin_id": admin_id,
                    "error": str(e),
                },
            )
            raise


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE ADMIN (COMPATIBILITY)
# ==============================================

async def create_admin(
    *,
    chat_id: int,
    username: str,
    full_name: str,
    role: str = "admin",
    password_hash: Optional[str] = None,
    session: AsyncSession,
) -> int:
    """
    إنشاء مدير جديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف الدردشة في Telegram
        username: اسم المستخدم
        full_name: الاسم الكامل
        role: دور المدير
        password_hash: هاش كلمة المرور
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        معرف المدير
    """
    repo = AdminRepository(session=session)

    admin_obj = await repo.create_admin(
        chat_id=chat_id,
        username=username,
        full_name=full_name,
        role=role,
        password_hash=password_hash,
    )

    return admin_obj.id


# ==============================================
# GET ADMIN BY CHAT ID (COMPATIBILITY)
# ==============================================

async def get_admin_by_chat_id(
    *,
    chat_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على مدير بواسطة معرف الدردشة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف الدردشة في Telegram
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قاموس بيانات المدير أو None
    """
    repo = AdminRepository(session=session)

    admin_obj = await repo.get_by_chat_id(
        chat_id=chat_id,
        only_active=True,
    )

    if not admin_obj:
        return None

    return {
        "id": admin_obj.id,
        "chat_id": admin_obj.chat_id,
        "username": admin_obj.username,
        "full_name": admin_obj.full_name,
        "role": admin_obj.role,
        "password_hash": admin_obj.password_hash,
        "created_at": admin_obj.created_at,
        "updated_at": admin_obj.updated_at,
        "is_active": admin_obj.is_active,
    }


# ==============================================
# GET ADMIN BY USERNAME (COMPATIBILITY)
# ==============================================

async def get_admin_by_username(
    *,
    username: str,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على مدير بواسطة اسم المستخدم (دالة متوافقة مع الإصدار القديم).
    
    Args:
        username: اسم المستخدم
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قاموس بيانات المدير أو None
    """
    repo = AdminRepository(session=session)

    admin_obj = await repo.get_by_username(
        username=username,
        only_active=True,
    )

    if not admin_obj:
        return None

    return {
        "id": admin_obj.id,
        "chat_id": admin_obj.chat_id,
        "username": admin_obj.username,
        "full_name": admin_obj.full_name,
        "role": admin_obj.role,
        "password_hash": admin_obj.password_hash,
        "created_at": admin_obj.created_at,
        "updated_at": admin_obj.updated_at,
        "is_active": admin_obj.is_active,
    }


# ==============================================
# ADMIN EXISTS (COMPATIBILITY)
# ==============================================

async def admin_exists(
    *,
    chat_id: int,
    session: AsyncSession,
) -> bool:
    """
    التحقق من وجود مدير (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف الدردشة في Telegram
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        True إذا كان المدير موجوداً، False وإلا
    """
    repo = AdminRepository(session=session)

    return await repo.exists(
        chat_id=chat_id,
        only_active=True,
    )


# ==============================================
# GET ALL ADMINS (COMPATIBILITY)
# ==============================================

async def get_all_admins(
    *,
    session: AsyncSession,
) -> AdminDictList:
    """
    الحصول على جميع المديرين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قائمة المديرين
    """
    repo = AdminRepository(session=session)

    admins = await repo.get_all(
        only_active=True,
    )

    result = []

    for admin in admins:
        result.append({
            "id": admin.id,
            "chat_id": admin.chat_id,
            "username": admin.username,
            "full_name": admin.full_name,
            "role": admin.role,
            "password_hash": admin.password_hash,
            "created_at": admin.created_at,
            "updated_at": admin.updated_at,
            "is_active": admin.is_active,
        })

    return result