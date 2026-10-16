# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 👑 ADMIN SERVICE
# منطق الأعمال للمديرين (CRUD الأساسي)
# ==============================================

"""MoulAI operational module for admin service.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.logger import logger
from app.core.security import hash_password
from app.repositories.admin.admin_repo import AdminRepository
from app.schemas.admin import (
    AdminCreate,
    AdminListResponse,
    AdminResponse,
    AdminUpdate,
)

# ==============================================
# 🧩 TYPES
# ==============================================

AdminStats = dict[str, Any]

# ==============================================
# 👑 ADMIN SERVICE
# ==============================================


class AdminService:
    """
    خدمة المديرين - تدير عمليات CRUD الأساسية للمديرين.

    مسؤول عن:
        - إنشاء المديرين
        - قراءة المديرين
        - تحديث المديرين
        - حذف المديرين
        - التحقق من صلاحيات المديرين

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
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
        تهيئة خدمة المديرين.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.admin_repo = AdminRepository(session)

    # ==========================================
    # 👑 ADMIN MANAGEMENT
    # ==========================================

    # ==============================================
    # CREATE ADMIN
    # ==============================================

    async def create_admin(
        self,
        *,
        admin_data: AdminCreate,
    ) -> AdminResponse:
        """
        إنشاء مدير جديد.

        Args:
            admin_data: بيانات المدير

        Returns:
            بيانات المدير المنشأ

        Raises:
            ConflictError: إذا كان اسم المستخدم أو chat_id موجوداً مسبقاً
        """
        logger.info(
            "admin_service_create_admin",
            extra={
                "username": admin_data.username,
                "chat_id": admin_data.chat_id,
            },
        )

        # التحقق من عدم وجود اسم المستخدم مسبقاً
        existing_by_username = await self.admin_repo.get_by_username(
            username=admin_data.username,
            only_active=False,
        )

        if existing_by_username:
            raise ConflictError(
                message=f"اسم المستخدم '{admin_data.username}' موجود مسبقاً",
            )

        # التحقق من عدم وجود chat_id مسبقاً
        existing_by_chat = await self.admin_repo.get_by_chat_id(
            chat_id=admin_data.chat_id,
            only_active=False,
        )

        if existing_by_chat:
            raise ConflictError(
                message=f"المدير بـ chat_id '{admin_data.chat_id}' موجود مسبقاً",
            )

        # تشفير كلمة المرور إذا كانت موجودة
        password_hash = None

        if admin_data.password:
            password_hash = hash_password(admin_data.password)

        # إنشاء المدير
        admin_obj = await self.admin_repo.create_admin(
            chat_id=admin_data.chat_id,
            username=admin_data.username,
            full_name=admin_data.full_name,
            role=admin_data.role or "admin",
            password_hash=password_hash,
            is_active=(
                admin_data.is_active if admin_data.is_active is not None else True
            ),
        )

        logger.info(
            "admin_service_create_admin_successful",
            extra={
                "admin_id": admin_obj.id,
                "username": admin_data.username,
            },
        )

        return AdminResponse.model_validate(admin_obj)

    # ==============================================
    # GET ADMIN BY ID
    # ==============================================

    async def get_admin_by_id(
        self,
        *,
        admin_id: int,
        include_inactive: bool = False,
    ) -> AdminResponse:
        """
        الحصول على مدير بواسطة المعرف.

        Args:
            admin_id: معرف المدير
            include_inactive: تضمين المديرين غير النشطين

        Returns:
            بيانات المدير

        Raises:
            NotFoundError: إذا لم يتم العثور على المدير
        """
        logger.info(
            "admin_service_get_admin_by_id",
            extra={
                "admin_id": admin_id,
                "include_inactive": include_inactive,
            },
        )

        admin_obj = await self.admin_repo.get_by_id(
            id=admin_id,
        )

        if not admin_obj:
            raise NotFoundError(
                message=f"المدير بـ ID '{admin_id}' غير موجود",
            )

        if not admin_obj.is_active and not include_inactive:
            raise NotFoundError(
                message=f"المدير بـ ID '{admin_id}' غير نشط",
            )

        return AdminResponse.model_validate(admin_obj)

    # ==============================================
    # GET ADMIN BY USERNAME
    # ==============================================

    async def get_admin_by_username(
        self,
        *,
        username: str,
        include_inactive: bool = False,
    ) -> AdminResponse:
        """
        الحصول على مدير بواسطة اسم المستخدم.

        Args:
            username: اسم المستخدم
            include_inactive: تضمين المديرين غير النشطين

        Returns:
            بيانات المدير

        Raises:
            NotFoundError: إذا لم يتم العثور على المدير
        """
        logger.info(
            "admin_service_get_admin_by_username",
            extra={
                "username": username,
                "include_inactive": include_inactive,
            },
        )

        admin_obj = await self.admin_repo.get_by_username(
            username=username,
            only_active=not include_inactive,
        )

        if not admin_obj:
            raise NotFoundError(
                message=f"المدير بـ username '{username}' غير موجود",
            )

        return AdminResponse.model_validate(admin_obj)

    # ==============================================
    # GET ADMIN BY CHAT ID
    # ==============================================

    async def get_admin_by_chat_id(
        self,
        *,
        chat_id: int,
        include_inactive: bool = False,
    ) -> AdminResponse:
        """
        الحصول على مدير بواسطة معرف الدردشة.

        Args:
            chat_id: معرف الدردشة في Telegram
            include_inactive: تضمين المديرين غير النشطين

        Returns:
            بيانات المدير

        Raises:
            NotFoundError: إذا لم يتم العثور على المدير
        """
        logger.info(
            "admin_service_get_admin_by_chat_id",
            extra={
                "chat_id": chat_id,
                "include_inactive": include_inactive,
            },
        )

        admin_obj = await self.admin_repo.get_by_chat_id(
            chat_id=chat_id,
            only_active=not include_inactive,
        )

        if not admin_obj:
            raise NotFoundError(
                message=f"المدير بـ chat_id '{chat_id}' غير موجود",
            )

        return AdminResponse.model_validate(admin_obj)

    # ==============================================
    # GET ALL ADMINS
    # ==============================================

    async def get_all_admins(
        self,
        *,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = "id",
        order_desc: bool = False,
    ) -> AdminListResponse:
        """
        الحصول على جميع المديرين.

        Args:
            only_active: جلب المديرين النشطين فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            order_by: حقل الترتيب
            order_desc: ترتيب تنازلي

        Returns:
            قائمة المديرين مع الإحصائيات
        """
        logger.info(
            "admin_service_get_all_admins",
            extra={
                "only_active": only_active,
                "skip": skip,
                "limit": limit,
            },
        )

        admins = await self.admin_repo.get_all(
            only_active=only_active,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc,
        )

        total = await self.admin_repo.count(
            filters={"is_active": True} if only_active else {},
        )

        return AdminListResponse(
            items=[AdminResponse.model_validate(admin) for admin in admins],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET ADMINS BY ROLE
    # ==============================================

    async def get_admins_by_role(
        self,
        *,
        role: str,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> AdminListResponse:
        """
        الحصول على المديرين حسب الدور.

        Args:
            role: دور المدير
            only_active: جلب المديرين النشطين فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة المديرين مع الإحصائيات
        """
        logger.info(
            "admin_service_get_admins_by_role",
            extra={
                "role": role,
                "only_active": only_active,
                "skip": skip,
                "limit": limit,
            },
        )

        admins = await self.admin_repo.get_by_role(
            role=role,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

        total = await self.admin_repo.count_by_role(
            role=role,
            only_active=only_active,
        )

        return AdminListResponse(
            items=[AdminResponse.model_validate(admin) for admin in admins],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # SEARCH ADMINS
    # ==============================================

    async def search_admins(
        self,
        *,
        query: str,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> AdminListResponse:
        """
        البحث عن المديرين.

        Args:
            query: نص البحث (username أو full_name)
            only_active: جلب المديرين النشطين فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة المديرين مع الإحصائيات
        """
        logger.info(
            "admin_service_search_admins",
            extra={
                "query": query,
                "only_active": only_active,
                "skip": skip,
                "limit": limit,
            },
        )

        admins = await self.admin_repo.search(
            query=query,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

        total = len(admins)

        return AdminListResponse(
            items=[AdminResponse.model_validate(admin) for admin in admins],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==========================================
    # ✏️ UPDATE OPERATIONS
    # ==========================================

    # ==============================================
    # UPDATE ADMIN
    # ==============================================

    async def update_admin(
        self,
        *,
        admin_id: int,
        update_data: AdminUpdate,
    ) -> AdminResponse:
        """
        تحديث بيانات المدير.

        Args:
            admin_id: معرف المدير
            update_data: بيانات التحديث

        Returns:
            بيانات المدير المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على المدير
            ConflictError: إذا كان اسم المستخدم موجوداً مسبقاً
        """
        logger.info(
            "admin_service_update_admin",
            extra={
                "admin_id": admin_id,
                "update_data": update_data.model_dump(exclude_unset=True),
            },
        )

        # التحقق من وجود المدير
        admin_obj = await self.admin_repo.get_by_id(id=admin_id)

        if not admin_obj:
            raise NotFoundError(
                message=f"المدير بـ ID '{admin_id}' غير موجود",
            )

        # تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)

        # التحقق من اسم المستخدم إذا تم تغييره
        if "username" in updates:
            existing = await self.admin_repo.get_by_username(
                username=updates["username"],
                only_active=False,
            )

            if existing and existing.id != admin_id:
                raise ConflictError(
                    message=f"اسم المستخدم '{updates['username']}' موجود مسبقاً",
                )

        # تشفير كلمة المرور إذا تم تغييرها
        if updates.get("password"):
            updates["password_hash"] = hash_password(updates["password"])
            del updates["password"]

        # تحديث المدير
        updated_admin = await self.admin_repo.update_admin(
            admin_id=admin_id,
            **updates,
        )

        if not updated_admin:
            raise NotFoundError(
                message=f"المدير بـ ID '{admin_id}' غير موجود",
            )

        logger.info(
            "admin_service_update_admin_successful",
            extra={
                "admin_id": admin_id,
                "updated_fields": list(updates.keys()),
            },
        )

        return AdminResponse.model_validate(updated_admin)

    # ==============================================
    # UPDATE ADMIN ROLE
    # ==============================================

    async def update_admin_role(
        self,
        *,
        admin_id: int,
        role: str,
    ) -> AdminResponse:
        """
        تحديث دور المدير.

        Args:
            admin_id: معرف المدير
            role: الدور الجديد

        Returns:
            بيانات المدير المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على المدير
        """
        logger.info(
            "admin_service_update_admin_role",
            extra={
                "admin_id": admin_id,
                "role": role,
            },
        )

        admin_obj = await self.admin_repo.update_role(
            admin_id=admin_id,
            role=role,
        )

        if not admin_obj:
            raise NotFoundError(
                message=f"المدير بـ ID '{admin_id}' غير موجود",
            )

        logger.info(
            "admin_service_update_admin_role_successful",
            extra={
                "admin_id": admin_id,
                "role": role,
            },
        )

        return AdminResponse.model_validate(admin_obj)

    # ==============================================
    # TOGGLE ADMIN STATUS
    # ==============================================

    async def toggle_admin_status(
        self,
        *,
        admin_id: int,
    ) -> AdminResponse:
        """
        تبديل حالة المدير (نشط/غير نشط).

        Args:
            admin_id: معرف المدير

        Returns:
            بيانات المدير المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على المدير
        """
        logger.info(
            "admin_service_toggle_admin_status",
            extra={"admin_id": admin_id},
        )

        admin_obj = await self.admin_repo.toggle_active(
            admin_id=admin_id,
        )

        if not admin_obj:
            raise NotFoundError(
                message=f"المدير بـ ID '{admin_id}' غير موجود",
            )

        logger.info(
            "admin_service_toggle_admin_status_successful",
            extra={
                "admin_id": admin_id,
                "is_active": admin_obj.is_active,
            },
        )

        return AdminResponse.model_validate(admin_obj)

    # ==============================================
    # ACTIVATE ADMIN
    # ==============================================

    async def activate_admin(
        self,
        *,
        admin_id: int,
    ) -> AdminResponse:
        """
        تنشيط المدير.

        Args:
            admin_id: معرف المدير

        Returns:
            بيانات المدير المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على المدير
        """
        logger.info(
            "admin_service_activate_admin",
            extra={"admin_id": admin_id},
        )

        admin_obj = await self.admin_repo.activate(
            admin_id=admin_id,
        )

        if not admin_obj:
            raise NotFoundError(
                message=f"المدير بـ ID '{admin_id}' غير موجود",
            )

        logger.info(
            "admin_service_activate_admin_successful",
            extra={"admin_id": admin_id},
        )

        return AdminResponse.model_validate(admin_obj)

    # ==============================================
    # DEACTIVATE ADMIN
    # ==============================================

    async def deactivate_admin(
        self,
        *,
        admin_id: int,
    ) -> AdminResponse:
        """
        إلغاء تنشيط المدير.

        Args:
            admin_id: معرف المدير

        Returns:
            بيانات المدير المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على المدير
        """
        logger.info(
            "admin_service_deactivate_admin",
            extra={"admin_id": admin_id},
        )

        admin_obj = await self.admin_repo.deactivate(
            admin_id=admin_id,
        )

        if not admin_obj:
            raise NotFoundError(
                message=f"المدير بـ ID '{admin_id}' غير موجود",
            )

        logger.info(
            "admin_service_deactivate_admin_successful",
            extra={"admin_id": admin_id},
        )

        return AdminResponse.model_validate(admin_obj)

    # ==============================================
    # DELETE ADMIN
    # ==============================================

    async def delete_admin(
        self,
        *,
        admin_id: int,
        permanent: bool = False,
    ) -> bool:
        """
        حذف المدير.

        Args:
            admin_id: معرف المدير
            permanent: حذف نهائي (بدلاً من الحذف المنطقي)

        Returns:
            True إذا تم الحذف

        Raises:
            NotFoundError: إذا لم يتم العثور على المدير
        """
        logger.info(
            "admin_service_delete_admin",
            extra={
                "admin_id": admin_id,
                "permanent": permanent,
            },
        )

        if permanent:
            # حذف نهائي
            result = await self.admin_repo.delete_permanently(
                admin_id=admin_id,
            )
        else:
            # حذف منطقي (تعيين is_active = False)
            result = await self.admin_repo.delete_admin(
                admin_id=admin_id,
            )

        if not result:
            raise NotFoundError(
                message=f"المدير بـ ID '{admin_id}' غير موجود",
            )

        logger.info(
            "admin_service_delete_admin_successful",
            extra={
                "admin_id": admin_id,
                "permanent": permanent,
            },
        )

        return True

    # ==========================================
    # 🔐 PERMISSION CHECKS
    # ==========================================

    # ==============================================
    # CHECK ADMIN PERMISSION
    # ==============================================

    async def check_admin_permission(
        self,
        *,
        admin_id: int,
        required_role: str | None = None,
        required_permission: str | None = None,
    ) -> bool:
        """
        التحقق من صلاحيات المدير.

        Args:
            admin_id: معرف المدير
            required_role: الدور المطلوب
            required_permission: الصلاحية المطلوبة

        Returns:
            True إذا كان المدير لديه الصلاحية

        Raises:
            NotFoundError: إذا لم يتم العثور على المدير
            UnauthorizedError: إذا لم يكن لدى المدير الصلاحية
        """
        logger.info(
            "admin_service_check_admin_permission",
            extra={
                "admin_id": admin_id,
                "required_role": required_role,
                "required_permission": required_permission,
            },
        )

        admin_obj = await self.admin_repo.get_authorization_context(
            admin_id=admin_id,
        )

        if not admin_obj:
            raise NotFoundError(
                message=f"المدير بـ ID '{admin_id}' غير موجود",
            )

        if not admin_obj.is_active:
            raise UnauthorizedError(
                message="المدير غير نشط",
            )

        role_record = admin_obj.role_record
        effective_role = role_record.code if role_record else admin_obj.role

        if required_role and effective_role not in {
            required_role,
            "super_admin",
        }:
            raise UnauthorizedError(
                message=f"المدير ليس لديه الدور المطلوب: {required_role}",
            )

        if required_permission:
            if not role_record or not role_record.is_active:
                raise UnauthorizedError(
                    message="لا يملك المدير دور RBAC نشطاً",
                )

            permission_codes = {
                permission.code for permission in role_record.permissions
            }
            if (
                "*" not in permission_codes
                and required_permission not in permission_codes
            ):
                raise UnauthorizedError(
                    message=f"المدير ليس لديه الصلاحية المطلوبة: {required_permission}",
                )

        return True

    # ==============================================
    # IS SUPER ADMIN
    # ==============================================

    async def is_super_admin(
        self,
        *,
        admin_id: int,
    ) -> bool:
        """
        التحقق من أن المدير هو مشرف عام.

        Args:
            admin_id: معرف المدير

        Returns:
            True إذا كان المدير مشرفاً عاماً
        """
        try:
            admin_obj = await self.admin_repo.get_by_id(id=admin_id)

            if not admin_obj:
                return False

            return admin_obj.role == "super_admin" and admin_obj.is_active

        except Exception as e:
            logger.exception(
                "admin_service_is_super_admin_failed",
                extra={
                    "admin_id": admin_id,
                    "error": str(e),
                },
            )
            return False

    # ==============================================
    # HAS ACTIVE CHAT
    # ==============================================

    async def has_active_chat(
        self,
        *,
        chat_id: int,
    ) -> bool:
        """Return whether an active administrator is linked to a chat identifier."""
        logger.info(
            "admin_service_has_active_chat",
            extra={"chat_id": chat_id},
        )

        admin = await self.admin_repo.get_by_chat_id(
            chat_id=chat_id,
            only_active=True,
        )
        return admin is not None

    # ==============================================
    # COUNT ADMINS
    # ==============================================

    async def count_admins(
        self,
        *,
        only_active: bool = True,
    ) -> int:
        """Count platform administrators, optionally restricted to active accounts."""
        logger.info(
            "admin_service_count_admins",
            extra={"only_active": only_active},
        )

        if only_active:
            return await self.admin_repo.count_active()
        return await self.admin_repo.count(filters={})

    # ==============================================
    # GET ADMIN STATISTICS
    # ==============================================

    async def get_admin_statistics(
        self,
    ) -> AdminStats:
        """
        الحصول على إحصائيات المديرين.

        Returns:
            قاموس الإحصائيات
        """
        logger.info("admin_service_get_admin_statistics")

        total = await self.admin_repo.count(filters={})
        active = await self.admin_repo.count_active()
        inactive = await self.admin_repo.count_inactive()

        roles = {
            "super_admin": await self.admin_repo.count_by_role(role="super_admin"),
            "admin": await self.admin_repo.count_by_role(role="admin"),
            "manager": await self.admin_repo.count_by_role(role="manager"),
        }

        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "roles": roles,
        }


# ==============================================
