# ==============================================
# 👤 USER REPOSITORY
# عمليات قاعدة البيانات للمستخدمين باستخدام SQLAlchemy
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.user import User
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

UserData = Dict[str, Any]
UserUpdateData = Dict[str, Any]
UserList = List[User]

# ==============================================
# 👤 USER REPOSITORY
# ==============================================


class UserRepository(BaseRepository[User, UserData, UserUpdateData]):
    """
    مستودع المستخدمين - يوفر عمليات خاصة بالمستخدمين.
    
    مسؤول عن:
        - عمليات CRUD الأساسية للمستخدمين
        - البحث والتصفية حسب chat_id والاسم والهاتف
        - إدارة موافقة المستخدم
    
    Attributes:
        model: نموذج User
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع المستخدمين.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(User, session)

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
    ) -> Optional[User]:
        """
        الحصول على مستخدم بواسطة chat_id.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            
        Returns:
            كائن User أو None
        """
        try:
            result = await self.session.execute(
                select(self.model)
                .where(self.model.chat_id == chat_id)
                .limit(1),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "user_repo_get_by_chat_id_failed",
                extra={
                    "chat_id": chat_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY PHONE
    # ==============================================

    async def get_by_phone(
        self,
        *,
        phone: str,
    ) -> Optional[User]:
        """
        الحصول على مستخدم بواسطة رقم الهاتف.
        
        Args:
            phone: رقم الهاتف
            
        Returns:
            كائن User أو None
        """
        try:
            result = await self.session.execute(
                select(self.model)
                .where(self.model.customer_phone == phone)
                .limit(1),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "user_repo_get_by_phone_failed",
                extra={
                    "phone": phone,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY NAME
    # ==============================================

    async def get_by_name(
        self,
        *,
        name: str,
        skip: int = 0,
        limit: int = 100,
    ) -> UserList:
        """
        البحث عن مستخدمين بواسطة الاسم.
        
        Args:
            name: اسم العميل
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة المستخدمين
        """
        try:
            query = (
                select(self.model)
                .where(self.model.customer_name.ilike(f"%{name}%"))
                .offset(skip)
                .limit(limit)
                .order_by(self.model.customer_name.asc())
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "user_repo_get_by_name_failed",
                extra={
                    "user_name": name,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY CONSENT
    # ==============================================

    async def get_by_consent(
        self,
        *,
        has_consent: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> UserList:
        """
        الحصول على المستخدمين حسب حالة الموافقة.
        
        Args:
            has_consent: حالة الموافقة (True = موافق، False = غير موافق)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة المستخدمين
        """
        try:
            query = (
                select(self.model)
                .where(self.model.consent == has_consent)
                .offset(skip)
                .limit(limit)
                .order_by(self.model.created_at.desc())
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "user_repo_get_by_consent_failed",
                extra={
                    "has_consent": has_consent,
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
        skip: int = 0,
        limit: int = 100,
    ) -> UserList:
        """
        البحث عن مستخدمين.
        
        Args:
            query: نص البحث (الاسم أو رقم الهاتف)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة المستخدمين
        """
        try:
            stmt = (
                select(self.model)
                .where(
                    or_(
                        self.model.customer_name.ilike(f"%{query}%"),
                        self.model.customer_phone.ilike(f"%{query}%"),
                    ),
                )
                .offset(skip)
                .limit(limit)
                .order_by(self.model.customer_name.asc())
            )

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "user_repo_search_failed",
                extra={
                    "query": query,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✅ CONSENT
    # ==========================================

    # ==============================================
    # HAS CONSENT
    # ==============================================

    async def has_consent(
        self,
        *,
        chat_id: int,
    ) -> bool:
        """
        التحقق مما إذا كان المستخدم قد أعطى موافقته.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            
        Returns:
            True إذا كان لديه موافقة، False إذا لم يكن
        """
        try:
            user = await self.get_by_chat_id(chat_id=chat_id)
            has_consent = user is not None and user.consent

            logger.info(
                "checked_consent",
                extra={
                    "chat_id": chat_id,
                    "has_consent": has_consent,
                },
            )

            return has_consent

        except Exception as e:
            logger.exception(
                "user_repo_has_consent_failed",
                extra={
                    "chat_id": chat_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GIVE CONSENT
    # ==============================================

    async def give_consent(
        self,
        *,
        chat_id: int,
    ) -> User:
        """
        منح الموافقة للمستخدم (إنشاء المستخدم إذا لم يكن موجوداً).
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            
        Returns:
            كائن User المنشأ أو المحدث
        """
        try:
            user = await self.get_by_chat_id(chat_id=chat_id)

            if user:
                # تحديث الموافقة
                user.consent = True
                await self.session.commit()
                await self.session.refresh(user)

                logger.info(
                    "consent_updated",
                    extra={
                        "chat_id": chat_id,
                        "user_id": user.id,
                    },
                )
            else:
                # إنشاء مستخدم جديد
                data: UserData = {
                    "chat_id": chat_id,
                    "consent": True,
                }

                user = await self.create(data=data)

                logger.info(
                    "user_created_with_consent",
                    extra={
                        "chat_id": chat_id,
                        "user_id": user.id,
                    },
                )

            logger.info(
                "consent_given",
                extra={"chat_id": chat_id},
            )

            return user

        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "user_repo_give_consent_failed",
                extra={
                    "chat_id": chat_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # REVOKE CONSENT
    # ==============================================

    async def revoke_consent(
        self,
        *,
        chat_id: int,
    ) -> Optional[User]:
        """
        إلغاء موافقة المستخدم.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            
        Returns:
            كائن User المحدث أو None
        """
        try:
            user = await self.get_by_chat_id(chat_id=chat_id)

            if not user:
                logger.warning(
                    "user_revoke_consent_user_not_found",
                    extra={"chat_id": chat_id},
                )
                return None

            # تحديث الموافقة إلى False
            user.consent = False
            await self.session.commit()
            await self.session.refresh(user)

            logger.info(
                "consent_revoked",
                extra={
                    "chat_id": chat_id,
                    "user_id": user.id,
                },
            )

            return user

        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "user_repo_revoke_consent_failed",
                extra={
                    "chat_id": chat_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ UPDATES
    # ==========================================

    # ==============================================
    # UPDATE NAME
    # ==============================================

    async def update_name(
        self,
        *,
        chat_id: int,
        customer_name: str,
    ) -> Optional[User]:
        """
        تحديث اسم العميل.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            customer_name: اسم العميل الجديد
            
        Returns:
            كائن User المحدث أو None
        """
        logger.info(
            "user_repo_update_name",
            extra={
                "chat_id": chat_id,
                "customer_name": customer_name,
            },
        )

        user = await self.get_by_chat_id(chat_id=chat_id)

        if not user:
            return None

        user.customer_name = customer_name
        await self.session.commit()
        await self.session.refresh(user)

        return user

    # ==============================================
    # UPDATE PHONE
    # ==============================================

    async def update_phone(
        self,
        *,
        chat_id: int,
        customer_phone: str,
    ) -> Optional[User]:
        """
        تحديث رقم هاتف العميل.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            customer_phone: رقم الهاتف الجديد
            
        Returns:
            كائن User المحدث أو None
        """
        logger.info(
            "user_repo_update_phone",
            extra={
                "chat_id": chat_id,
                "customer_phone": customer_phone,
            },
        )

        user = await self.get_by_chat_id(chat_id=chat_id)

        if not user:
            return None

        user.customer_phone = customer_phone
        await self.session.commit()
        await self.session.refresh(user)

        return user

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT WITH CONSENT
    # ==============================================

    async def count_with_consent(
        self,
    ) -> int:
        """
        حساب عدد المستخدمين الذين لديهم موافقة.
        
        Returns:
            عدد المستخدمين بالموافقة
        """
        return await self.count(filters={"consent": True})

    # ==============================================
    # COUNT WITHOUT CONSENT
    # ==============================================

    async def count_without_consent(
        self,
    ) -> int:
        """
        حساب عدد المستخدمين الذين ليس لديهم موافقة.
        
        Returns:
            عدد المستخدمين بدون موافقة
        """
        return await self.count(filters={"consent": False})

    # ==============================================
    # COUNT WITH NAME
    # ==============================================

    async def count_with_name(
        self,
    ) -> int:
        """
        حساب عدد المستخدمين الذين لديهم اسم.
        
        Returns:
            عدد المستخدمين بالاسم
        """
        try:
            result = await self.session.execute(
                select(func.count())
                .select_from(self.model)
                .where(self.model.customer_name.is_not(None)),
            )

            return result.scalar_one()

        except Exception as e:
            logger.exception(
                "user_repo_count_with_name_failed",
                extra={"error": str(e)},
            )
            raise

    # ==============================================
    # COUNT WITH PHONE
    # ==============================================

    async def count_with_phone(
        self,
    ) -> int:
        """
        حساب عدد المستخدمين الذين لديهم رقم هاتف.
        
        Returns:
            عدد المستخدمين برقم الهاتف
        """
        try:
            result = await self.session.execute(
                select(func.count())
                .select_from(self.model)
                .where(self.model.customer_phone.is_not(None)),
            )

            return result.scalar_one()

        except Exception as e:
            logger.exception(
                "user_repo_count_with_phone_failed",
                extra={"error": str(e)},
            )
            raise


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# HAS CONSENT (COMPATIBILITY)
# ==============================================

async def has_consent(
    *,
    chat_id: int,
    session: AsyncSession,
) -> bool:
    """
    التحقق مما إذا كان المستخدم قد أعطى موافقته (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف المستخدم في تيليجرام
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        True إذا كان لديه موافقة، False إذا لم يكن
    """
    repo = UserRepository(session=session)

    return await repo.has_consent(chat_id=chat_id)


# ==============================================
# GIVE CONSENT (COMPATIBILITY)
# ==============================================

async def give_consent(
    *,
    chat_id: int,
    session: AsyncSession,
) -> None:
    """
    منح الموافقة للمستخدم (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف المستخدم في تيليجرام
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = UserRepository(session=session)

    await repo.give_consent(chat_id=chat_id)

    logger.info(
        "consent_given",
        extra={"chat_id": chat_id},
    )


# ==============================================
# REVOKE CONSENT (COMPATIBILITY)
# ==============================================

async def revoke_consent(
    *,
    chat_id: int,
    session: AsyncSession,
) -> None:
    """
    إلغاء موافقة المستخدم (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف المستخدم في تيليجرام
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = UserRepository(session=session)

    await repo.revoke_consent(chat_id=chat_id)

    logger.info(
        "consent_revoked",
        extra={"chat_id": chat_id},
    )


# ==============================================
# GET USER BY CHAT ID (COMPATIBILITY)
# ==============================================

async def get_user_by_chat_id(
    *,
    chat_id: int,
    session: AsyncSession,
) -> Optional[User]:
    """
    الحصول على مستخدم بواسطة chat_id (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف المستخدم في تيليجرام
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        كائن User أو None
    """
    repo = UserRepository(session=session)

    return await repo.get_by_chat_id(chat_id=chat_id)


# ==============================================
# CREATE USER (COMPATIBILITY)
# ==============================================

async def create_user(
    *,
    chat_id: int,
    consent: bool = False,
    customer_name: Optional[str] = None,
    customer_phone: Optional[str] = None,
    session: AsyncSession,
) -> User:
    """
    إنشاء مستخدم جديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف المستخدم في تيليجرام
        consent: حالة الموافقة
        customer_name: اسم العميل (اختياري)
        customer_phone: رقم هاتف العميل (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        كائن User المنشأ
    """
    repo = UserRepository(session=session)

    data: UserData = {
        "chat_id": chat_id,
        "consent": consent,
    }

    if customer_name is not None:
        data["customer_name"] = customer_name

    if customer_phone is not None:
        data["customer_phone"] = customer_phone

    user = await repo.create(data=data)

    logger.info(
        "user_created",
        extra={
            "user_id": user.id,
            "chat_id": chat_id,
        },
    )

    return user