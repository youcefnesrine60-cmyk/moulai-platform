# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📦 BASE REPOSITORY
# النموذج الأساسي لجميع المستودعات
# يوفر عمليات CRUD مشتركة لجميع النماذج
# ==============================================

from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
)

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.logger import logger
from app.models.base import BaseModel


# ==============================================
# 🧩 TYPES
# ==============================================

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=Dict[str, Any])
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=Dict[str, Any])
FilterType = Optional[Dict[str, Any]]


# ==============================================
# 📦 BASE REPOSITORY
# ==============================================

class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    المستودع الأساسي - يوفر عمليات CRUD مشتركة.
    
    مسؤول عن:
        - عمليات الإنشاء (create, create_many)
        - عمليات القراءة (get_by_id, get_all, count, exists)
        - عمليات التحديث (update)
        - عمليات الحذف (delete, delete_many)
    
    ⚠️ يدعم النماذج التي تحتوي على `id` والنماذج التي لا تحتوي عليه
       (مثل RestaurantMetric و RestaurantOrderCounter)
    
    Attributes:
        model: نموذج SQLAlchemy
        session: جلسة قاعدة البيانات غير المتزامنة
        _primary_key_name: اسم المفتاح الأساسي (id أو غيره)
    """

    def __init__(
        self,
        model: Type[ModelType],
        session: AsyncSession,
    ) -> None:
        """
        تهيئة المستودع.
        
        Args:
            model: نموذج SQLAlchemy
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.model = model
        self.session = session
        self._primary_key_name = self._detect_primary_key_name()

    # ==========================================
    # 🔧 PRIVATE HELPERS
    # ==========================================

    def _detect_primary_key_name(self) -> str:
        """
        تحديد اسم المفتاح الأساسي للنموذج.
        
        ✅ يدعم النماذج التي لا تحتوي على `id`
           (مثل RestaurantMetric الذي يستخدم restaurant_id)
        
        Returns:
            str: اسم المفتاح الأساسي
        """
        # فحص المفتاح الأساسي عبر SQLAlchemy
        if hasattr(self.model, "__table__"):
            primary_keys = list(self.model.__table__.primary_key.columns)
            if primary_keys:
                return primary_keys[0].name

        # افتراضياً: id
        return "id"

    def _get_primary_key_value(
        self,
        instance: ModelType,
    ) -> Any:
        """
        الحصول على قيمة المفتاح الأساسي من نسخة النموذج.
        
        Args:
            instance: نسخة من النموذج
            
        Returns:
            Any: قيمة المفتاح الأساسي
        """
        return getattr(instance, self._primary_key_name, None)

    # ==========================================
    # 📥 CREATE
    # ==========================================

    async def create(
        self,
        *,
        data: CreateSchemaType,
    ) -> ModelType:
        """
        إنشاء سجل جديد.
        
        ✅ التصحيح النهائي: استخدام commit() و refresh()
        
        Args:
            data: بيانات الإنشاء
            
        Returns:
            ModelType: النموذج المُنشأ
        """
        try:
            instance = self.model(**data)
            self.session.add(instance)

            await self.session.flush()
            await self.session.commit()

            instance_id = self._get_primary_key_value(instance)
            refreshed = await self.get_by_id(id=instance_id)

            logger.info(
                f"{self.model.__name__}_created",
                extra={"id": instance_id},
            )

            return refreshed or instance

        except IntegrityError as e:
            await self.session.rollback()
            logger.warning(
                f"{self.model.__name__}_create_integrity_error",
                extra={"error": str(e)},
            )
            raise
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                f"{self.model.__name__}_create_failed",
                extra={"error": str(e)},
            )
            raise

    # ==============================================
    # CREATE MANY
    # ==============================================

    async def create_many(
        self,
        *,
        data_list: List[CreateSchemaType],
    ) -> List[ModelType]:
        """
        إنشاء عدة سجلات دفعة واحدة.
        
        Args:
            data_list: قائمة بيانات الإنشاء
            
        Returns:
            List[ModelType]: قائمة النماذج المُنشأة
        """
        try:
            instances = [self.model(**data) for data in data_list]
            self.session.add_all(instances)

            await self.session.flush()
            await self.session.commit()

            refreshed_instances = []
            for instance in instances:
                instance_id = self._get_primary_key_value(instance)
                refreshed = await self.get_by_id(id=instance_id)
                refreshed_instances.append(refreshed or instance)

            logger.info(
                f"{self.model.__name__}_many_created",
                extra={"count": len(instances)},
            )

            return refreshed_instances

        except IntegrityError as e:
            await self.session.rollback()
            logger.warning(
                f"{self.model.__name__}_create_many_integrity_error",
                extra={"error": str(e)},
            )
            raise
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                f"{self.model.__name__}_create_many_failed",
                extra={"error": str(e)},
            )
            raise

    # ==========================================
    # 📖 READ
    # ==========================================

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        id: int,
    ) -> Optional[ModelType]:
        """
        الحصول على سجل بالمعرف.
        
        ✅ التصحيح: دعم النماذج التي لا تحتوي على `id`
           (مثل RestaurantMetric الذي يستخدم restaurant_id)
        
        Args:
            id: المعرف
            
        Returns:
            Optional[ModelType]: النموذج أو None
        """
        try:
            # ✅ استخدام اسم المفتاح الأساسي الديناميكي
            pk_column = getattr(self.model, self._primary_key_name)

            result = await self.session.execute(
                select(self.model).where(pk_column == id),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                f"{self.model.__name__}_get_by_id_failed",
                extra={
                    "id": id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET ALL
    # ==============================================

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: FilterType = None,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> List[ModelType]:
        """
        الحصول على جميع السجلات مع ترقيم الصفحات.
        
        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            filters: عوامل التصفية
            order_by: اسم العمود للترتيب
            descending: ترتيب تنازلي
            
        Returns:
            List[ModelType]: قائمة النماذج
        """
        try:
            query = select(self.model)

            # تطبيق الفلاتر
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key) and value is not None:
                        query = query.where(
                            getattr(self.model, key) == value,
                        )

            # تطبيق الترتيب
            if order_by and hasattr(self.model, order_by):
                column = getattr(self.model, order_by)
                query = query.order_by(
                    column.desc() if descending else column.asc(),
                )

            # تطبيق الترقيم
            query = query.offset(skip).limit(limit)

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                f"{self.model.__name__}_get_all_failed",
                extra={"error": str(e)},
            )
            raise

    # ==============================================
    # COUNT
    # ==============================================

    async def count(
        self,
        *,
        filters: FilterType = None,
    ) -> int:
        """
        حساب عدد السجلات.
        
        Args:
            filters: عوامل التصفية
            
        Returns:
            int: عدد السجلات
        """
        try:
            query = select(func.count()).select_from(self.model)

            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key) and value is not None:
                        query = query.where(
                            getattr(self.model, key) == value,
                        )

            result = await self.session.execute(query)

            return result.scalar_one() or 0

        except Exception as e:
            logger.exception(
                f"{self.model.__name__}_count_failed",
                extra={"error": str(e)},
            )
            raise

    # ==============================================
    # EXISTS
    # ==============================================

    async def exists(
        self,
        *,
        id: int,
    ) -> bool:
        """
        التحقق من وجود سجل.
        
        ✅ التصحيح: دعم النماذج التي لا تحتوي على `id`
        
        Args:
            id: المعرف
            
        Returns:
            bool: True إذا كان موجوداً، False إذا لم يكن
        """
        try:
            pk_column = getattr(self.model, self._primary_key_name)

            result = await self.session.execute(
                select(func.count())
                .where(pk_column == id)
                .select_from(self.model),
            )

            return result.scalar_one() > 0

        except Exception as e:
            logger.exception(
                f"{self.model.__name__}_exists_failed",
                extra={
                    "id": id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ UPDATE
    # ==========================================

    # ==============================================
    # UPDATE
    # ==============================================

    async def update(
        self,
        *,
        id: int,
        data: UpdateSchemaType,
    ) -> Optional[ModelType]:
        """
        تحديث سجل.
        
        ✅ التصحيح: دعم النماذج التي لا تحتوي على `id`
           (مثل RestaurantMetric الذي يستخدم restaurant_id)
        
        Args:
            id: المعرف
            data: بيانات التحديث
            
        Returns:
            Optional[ModelType]: النموذج المُحدّث أو None
        """
        try:
            # ✅ استخدام اسم المفتاح الأساسي الديناميكي
            instance = await self.get_by_id(id=id)

            if not instance:
                return None

            for key, value in data.items():
                if hasattr(instance, key) and value is not None:
                    setattr(instance, key, value)

            await self.session.flush()
            await self.session.commit()

            refreshed = await self.get_by_id(id=id)

            logger.info(
                f"{self.model.__name__}_updated",
                extra={"id": id},
            )

            return refreshed or instance

        except Exception as e:
            await self.session.rollback()
            logger.exception(
                f"{self.model.__name__}_update_failed",
                extra={
                    "id": id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # 🗑️ DELETE
    # ==========================================

    # ==============================================
    # DELETE
    # ==============================================

    async def delete(
        self,
        *,
        id: int,
    ) -> bool:
        """
        حذف سجل.
        
        ✅ التصحيح: دعم النماذج التي لا تحتوي على `id`
        
        Args:
            id: المعرف
            
        Returns:
            bool: True إذا تم الحذف، False إذا لم يتم
        """
        try:
            instance = await self.get_by_id(id=id)

            if not instance:
                return False

            await self.session.delete(instance)

            # ✅ استخدام commit()
            await self.session.commit()

            logger.info(
                f"{self.model.__name__}_deleted",
                extra={"id": id},
            )

            return True

        except Exception as e:
            await self.session.rollback()
            logger.exception(
                f"{self.model.__name__}_delete_failed",
                extra={
                    "id": id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # DELETE MANY
    # ==============================================

    async def delete_many(
        self,
        *,
        ids: List[int],
    ) -> int:
        """
        حذف عدة سجلات.
        
        ✅ التصحيح: دعم النماذج التي لا تحتوي على `id`
        
        Args:
            ids: قائمة المعرفات
            
        Returns:
            int: عدد السجلات المحذوفة
        """
        try:
            pk_column = getattr(self.model, self._primary_key_name)

            result = await self.session.execute(
                select(self.model).where(pk_column.in_(ids)),
            )

            instances = list(result.scalars().all())

            for instance in instances:
                await self.session.delete(instance)

            # ✅ استخدام commit()
            await self.session.commit()

            logger.info(
                f"{self.model.__name__}_many_deleted",
                extra={"count": len(instances)},
            )

            return len(instances)

        except Exception as e:
            await self.session.rollback()
            logger.exception(
                f"{self.model.__name__}_delete_many_failed",
                extra={"error": str(e)},
            )
            raise

    # ==========================================
    # 📊 EXTRA
    # ==========================================

    # ==============================================
    # COUNT RESTAURANTS
    # ==============================================

    async def count_restaurants(
        self,
        *,
        owner_id: int,
    ) -> int:
        """
        حساب عدد المطاعم المملوكة لمالك معين.
        
        Args:
            owner_id: معرف المالك
            
        Returns:
            int: عدد المطاعم
        """
        try:
            from app.models.restaurant import Restaurant

            result = await self.session.execute(
                select(func.count())
                .select_from(Restaurant)
                .where(Restaurant.owner_id == owner_id),
            )

            return result.scalar_one() or 0

        except Exception as e:
            logger.exception(
                "count_restaurants_failed",
                extra={
                    "owner_id": owner_id,
                    "error": str(e),
                },
            )
            raise


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "BaseRepository",
    "ModelType",
    "CreateSchemaType",
    "UpdateSchemaType",
    "FilterType",
]