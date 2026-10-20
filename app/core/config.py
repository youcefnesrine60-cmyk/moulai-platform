# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ⚙️ APPLICATION CONFIGURATION
# إدارة إعدادات التطبيق من ملف .env
# ==============================================

"""MoulAI operational module for config.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Literal,
    Self,
    TypeAlias,
)

from dotenv import load_dotenv
from pydantic import (
    ConfigDict,
    Field,
    SecretStr,
    model_validator,
)
from pydantic_settings import BaseSettings

from app.core.health_only import validate_health_only_configuration
from app.core.logger import logger

# ==============================================
# 🌍 LOAD ENVIRONMENT VARIABLES
# ==============================================

load_dotenv()

# ==============================================
# DATABASE TARGET TYPE
# ==============================================

DatabaseTarget: TypeAlias = Literal["primary", "development"]

# ==============================================
# ⚙️ SETTINGS
# ==============================================


class Settings(BaseSettings):
    """
    إعدادات التطبيق

    يتم قراءة القيم من ملف .env

    Attributes:
        APP_ENV: بيئة التشغيل (development, test, staging, production)
        DEBUG: وضع التصحيح
        APP_NAME: اسم التطبيق
        APP_VERSION: إصدار التطبيق
        APP_URL: رابط التطبيق
        DATABASE_URL: رابط قاعدة البيانات (مع +asyncpg)
        DATABASE_TARGET: اختيار اتصال التطبيق الصريح دون تعديل الرابط الأساسي
        DATABASE_SYNC_URL: رابط قاعدة البيانات (بدون +asyncpg)
        REDIS_URL: رابط Redis
        BOT_TOKEN: رمز بوت Telegram
        WEBHOOK_URL: رابط Webhook
        WEBHOOK_PATH: مسار Webhook
        OPENAI_API_KEY: مفتاح OpenAI API
        OPENAI_BASE_URL: رابط OpenAI API
        AI_MODEL: نموذج الذكاء الاصطناعي
        SECRET_KEY: المفتاح السري
        ALLOWED_ORIGINS: النطاقات المسموحة لـ CORS
        DB_ECHO: تفعيل تسجيل استعلامات SQL
        DB_POOL_SIZE: حجم تجمع الاتصالات
        DB_MAX_OVERFLOW: الحد الأقصى للاتصالات الإضافية
        DB_POOL_TIMEOUT: مهلة تجمع الاتصالات
        DB_POOL_PRE_PING: التحقق من الاتصال قبل الاستخدام
        DB_POOL_RECYCLE: إعادة تدوير الاتصالات
        REDIS_POOL_SIZE: حجم تجمع Redis
        REDIS_POOL_TIMEOUT: مهلة تجمع Redis
        RATE_LIMIT_PER_MINUTE: الحد الأقصى للطلبات في الدقيقة
        RATE_LIMIT_PER_HOUR: الحد الأقصى للطلبات في الساعة
        LOG_LEVEL: مستوى التسجيل
        LOG_FORMAT: تنسيق التسجيل
        LOG_FILE_PATH: مسار ملف التسجيل
        DEFAULT_SUBSCRIPTION_PLAN: خطة الاشتراك الافتراضية
        TRIAL_PERIOD_DAYS: مدة الفترة التجريبية بالأيام
        MAX_RESTAURANTS_PER_OWNER: الحد الأقصى للمطاعم لكل مالك
        TENANT_ISOLATION_LEVEL: مستوى عزل المستأجرين
    """

    # ==========================================
    # 🌐 GENERAL
    # ==========================================

    APP_ENV: str = Field(
        default="development",
        description="بيئة التشغيل: development, test, staging, production",
    )
    HEALTH_ONLY_MODE: bool = Field(
        default=False,
        description="Explicit development observation: GET / and /health only",
    )
    DEBUG: bool = Field(
        default=True,
        description="وضع التصحيح",
    )
    APP_NAME: str = Field(
        default="MoulAI",
        description="اسم التطبيق",
    )
    APP_VERSION: str = Field(
        default="1.0.0",
        description="إصدار التطبيق",
    )
    APP_URL: str = Field(
        default="https://onrender.com",
        description="رابط التطبيق",
    )

    # ==========================================
    # 🐘 DATABASE
    # ==========================================

    DATABASE_TARGET: DatabaseTarget = Field(
        default="primary",
        description=(
            "ORM connection target: primary preserves DATABASE_URL; development "
            "requires the verified TEST_DATABASE_URL and development/test APP_ENV"
        ),
    )
    DATABASE_URL: str = Field(
        default="",
        description="رابط قاعدة البيانات (مع +asyncpg)",
        json_schema_extra={
            "example": "postgresql+asyncpg://user:pass@localhost:5432/db"
        },
    )
    DATABASE_SYNC_URL: str | None = Field(
        default=None,
        description="رابط قاعدة البيانات (بدون +asyncpg - لـ Psycopg3)",
        json_schema_extra={"example": "postgresql://user:pass@localhost:5432/db"},
    )

    # ==========================================
    # 🔴 REDIS
    # ==========================================
    # TEST DATABASE
    # ==========================================

    TEST_DATABASE_URL: str = Field(
        default="",
        description="Explicit isolated asynchronous database URL for tests",
    )
    TEST_DATABASE_SYNC_URL: str | None = Field(
        default=None,
        description="Optional synchronous test database URL for migration tooling",
    )
    TEST_DATABASE_ENDPOINT_ID: str | None = Field(
        default=None,
        description="Verified Neon development endpoint ID for isolated tests",
    )
    PROTECTED_DATABASE_ENDPOINT_ID: str | None = Field(
        default=None,
        description="Protected production Neon endpoint excluded from test tooling",
    )
    TEST_DATABASE_BRANCH_ID: str | None = Field(
        default=None,
        description="Verified Neon development branch ID for test identity checks",
    )
    TEST_DATABASE_PROJECT_ID: str | None = Field(
        default=None,
        description="Verified Neon project ID containing the development branch",
    )
    PROTECTED_DATABASE_BRANCH_ID: str | None = Field(
        default=None,
        description="Protected production branch excluded from test identity checks",
    )
    # ==========================================

    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="رابط Redis",
        json_schema_extra={"example": "redis://localhost:6379/0"},
    )

    # ==========================================
    # 🤖 TELEGRAM
    # ==========================================

    BOT_TOKEN: str = Field(
        default="",
        description="رمز بوت Telegram",
        min_length=1,
    )
    WEBHOOK_URL: str = Field(
        default="",
        description="رابط Webhook",
        json_schema_extra={"example": "https://your-domain.com/webhook"},
    )
    WEBHOOK_PATH: str = Field(
        default="/webhook",
        description="مسار Webhook",
    )
    TELEGRAM_WEBHOOK_SECRET_TOKEN: SecretStr | None = Field(
        default=None,
        description="Secret token configured with Telegram setWebhook",
    )
    # Phase-one manual subscription billing providers.
    MANUAL_CCP_ENABLED: bool = True
    MANUAL_BARIDIMOB_ENABLED: bool = True
    MANUAL_TRANSFER_BENEFICIARY: str | None = Field(default=None, max_length=255)
    MANUAL_CCP_ACCOUNT: str | None = Field(default=None, max_length=100)
    MANUAL_CCP_KEY: str | None = Field(default=None, max_length=10)
    MANUAL_BARIDIMOB_RIP: str | None = Field(default=None, max_length=100)

    # ==========================================
    # 🤖 AI
    # ==========================================

    OPENAI_API_KEY: str = Field(
        default="",
        description="مفتاح OpenAI API",
        min_length=1,
    )
    OPENAI_BASE_URL: str = Field(
        default="https://api.openai.com/v1",
        description="رابط OpenAI API (مخصص)",
    )
    AI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="نموذج الذكاء الاصطناعي",
    )

    # ==========================================
    # 🔐 SECURITY
    # ==========================================

    SECRET_KEY: str = Field(
        default="",
        description="المفتاح السري للتطبيق",
        min_length=32,
    )
    OIDC_ISSUER: str | None = Field(
        default=None,
        description="Issuer URL for the trusted OpenID Connect provider",
    )
    OIDC_AUDIENCE: str | None = Field(
        default=None,
        description="Expected audience for API access tokens",
    )
    OIDC_JWKS_URL: str | None = Field(
        default=None,
        description="HTTPS URL of the trusted provider's JWKS endpoint",
    )
    # Observation safety flags only; no diagnostics or local HTTP auth is added.
    OIDC_DIAGNOSTICS_ENABLED: bool = Field(
        default=False,
        description="Must remain false for Health-Only observation",
    )
    OIDC_ALLOW_LOCAL_HTTP: bool = Field(
        default=False,
        description="Must remain false for Health-Only observation",
    )

    # ==========================================
    # 🌐 CORS
    # ==========================================

    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000",
        description="النطاقات المسموحة لـ CORS (مفصولة بفواصل)",
    )

    # ==========================================
    # 📊 PERFORMANCE & RATE LIMITING
    # ==========================================

    DB_ECHO: bool = Field(
        default=False,
        description="تفعيل تسجيل استعلامات SQL (يتم ضبطها تلقائياً حسب البيئة)",
    )
    DB_POOL_SIZE: int = Field(
        default=20,
        ge=1,
        description="حجم تجمع الاتصالات",
    )
    DB_MAX_OVERFLOW: int = Field(
        default=20,
        ge=0,
        description="الحد الأقصى للاتصالات الإضافية",
    )
    DB_POOL_TIMEOUT: int = Field(
        default=30,
        ge=1,
        description="مهلة تجمع الاتصالات (ثواني)",
    )
    DB_POOL_PRE_PING: bool = Field(
        default=True,
        description="التحقق من الاتصال قبل الاستخدام",
    )
    DB_POOL_RECYCLE: int = Field(
        default=3600,
        ge=60,
        description="إعادة تدوير الاتصالات (ثواني)",
    )

    REDIS_POOL_SIZE: int = Field(
        default=10,
        ge=1,
        description="حجم تجمع Redis",
    )
    REDIS_POOL_TIMEOUT: int = Field(
        default=5,
        ge=1,
        description="مهلة تجمع Redis (ثواني)",
    )

    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60,
        ge=1,
        description="الحد الأقصى للطلبات في الدقيقة",
    )
    RATE_LIMIT_PER_HOUR: int = Field(
        default=1000,
        ge=1,
        description="الحد الأقصى للطلبات في الساعة",
    )

    # ==========================================
    # 📝 LOGGING
    # ==========================================

    LOG_LEVEL: str = Field(
        default="INFO",
        description="مستوى التسجيل (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    LOG_FORMAT: str = Field(
        default="json",
        description="تنسيق التسجيل (json, text)",
    )
    LOG_FILE_PATH: str = Field(
        default="logs/app.log",
        description="مسار ملف التسجيل",
    )

    # ==========================================
    # 🏪 SUBSCRIPTION
    # ==========================================

    DEFAULT_SUBSCRIPTION_PLAN: str = Field(
        default="basic",
        description="خطة الاشتراك الافتراضية",
    )
    TRIAL_PERIOD_DAYS: int = Field(
        default=14,
        ge=1,
        description="مدة الفترة التجريبية بالأيام",
    )
    MAX_RESTAURANTS_PER_OWNER: int = Field(
        default=10,
        ge=1,
        description="الحد الأقصى للمطاعم لكل مالك",
    )
    TENANT_ISOLATION_LEVEL: str = Field(
        default="strict",
        description="مستوى عزل المستأجرين (strict, loose, none)",
    )

    # ==========================================
    # 🛠️ HELPER PROPERTIES
    # ==========================================

    @property
    def IS_DEVELOPMENT(self) -> bool:
        """
        التحقق مما إذا كانت البيئة هي Development.

        Returns:
            True إذا كانت البيئة Development
        """
        return self.APP_ENV == "development"

    # ==============================================
    # IS PRODUCTION
    # ==============================================

    @property
    def IS_PRODUCTION(self) -> bool:
        """
        التحقق مما إذا كانت البيئة هي Production.

        Returns:
            True إذا كانت البيئة Production
        """
        return self.APP_ENV == "production"

    # ==============================================
    # IS TESTING
    # ==============================================

    @property
    def IS_TESTING(self) -> bool:
        """
        التحقق مما إذا كانت البيئة هي Testing.

        Returns:
            True إذا كانت البيئة Testing
        """
        return self.APP_ENV == "testing"

    # ==============================================
    # VALIDATE THE OPT-IN OBSERVATION PROFILE
    # ==============================================

    @model_validator(mode="after")
    def validate_health_only_profile(self) -> Self:
        """Reject unsafe observation settings before any engine is constructed."""
        validate_health_only_configuration(configuration=self)
        return self

    # ==============================================
    # DB ECHO ENABLED
    # ==============================================

    @property
    def DB_ECHO_ENABLED(self) -> bool:
        """
        تحديد ما إذا كان سيتم طباعة استعلامات SQL.

        يتم تفعيلها تلقائياً في بيئة التطوير.

        Returns:
            True إذا كان يجب تفعيل تسجيل SQL
        """
        return self.IS_DEVELOPMENT and self.DEBUG

    # ==============================================
    # ALLOWED ORIGINS LIST
    # ==============================================

    @property
    def ALLOWED_ORIGINS_LIST(self) -> list[str]:
        """
        تحويل ALLOWED_ORIGINS إلى قائمة.

        Returns:
            قائمة النطاقات المسموحة
        """
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    # ==========================================
    # 🔧 MODEL CONFIG
    # ==========================================

    # استخدام ConfigDict بدلاً من class-based config
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # تجاهل أي متغيرات زائدة
    )


# ==============================================
# 🌍 GLOBAL INSTANCE
# ==============================================

# إنشاء كائن الإعدادات لاستخدامه في كل مكان
settings: Settings = Settings()

# ==============================================
# 🔄 APPLY DYNAMIC DB_ECHO
# ==============================================

# ضبط DB_ECHO تلقائياً حسب البيئة
settings.DB_ECHO = settings.DB_ECHO_ENABLED

logger.info(
    "settings_initialized",
    extra={
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "app_env": settings.APP_ENV,
        "database_target": settings.DATABASE_TARGET,
        "debug": settings.DEBUG,
        "db_echo": settings.DB_ECHO,
    },
)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "DatabaseTarget",
    "Settings",
    "settings",
]
