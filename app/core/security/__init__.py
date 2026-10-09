# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PACKAGE INITIALIZER - APP / CORE / SECURITY /   INIT
# Package initialization and public exports component.
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
    Dict,
    Optional,
    Union,
)
import secrets
import base64
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

from app.core.config import settings

# ==============================================
# 🔑 PASSWORD HASHING
# ==============================================

# إعداد سياق تشفير كلمات المرور
pwd_context = CryptContext(
    schemes=["bcrypt"],  # استخدام خوارزمية bcrypt
    deprecated="auto",  # تمييز الخوارزميات القديمة تلقائياً
)


# ==============================================
# HASH PASSWORD
# ==============================================


def hash_password(
    password: str,
) -> str:
    """
    تشفير كلمة المرور باستخدام bcrypt.

    Args:
        password: كلمة المرور النصية

    Returns:
        النص المشفر
    """
    return pwd_context.hash(password)


# ==============================================
# VERIFY PASSWORD
# ==============================================


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    التحقق من صحة كلمة المرور.

    Args:
        plain_password: كلمة المرور النصية
        hashed_password: النص المشفر المخزن

    Returns:
        True إذا كانت صحيحة، False وإلا
    """
    return pwd_context.verify(plain_password, hashed_password)


# ==============================================
# GET PASSWORD HASH
# ==============================================


def get_password_hash(
    password: str,
) -> str:
    """
    الحصول على هاش كلمة المرور (مرادف لـ hash_password).

    Args:
        password: كلمة المرور النصية

    Returns:
        النص المشفر
    """
    return hash_password(password)


# ==============================================
# 🎫 TOKEN GENERATION
# ==============================================


def generate_session_token(
    length: int = 64,
) -> str:
    """
    توليد رمز جلسة عشوائي وآمن.

    Args:
        length: طول الرمز (الافتراضي: 64)

    Returns:
        رمز الجلسة
    """
    return secrets.token_urlsafe(length)


# ==============================================
# GENERATE VERIFICATION TOKEN
# ==============================================


def generate_verification_token(
    length: int = 32,
) -> str:
    """
    توليد رمز تحقق عشوائي.

    Args:
        length: طول الرمز (الافتراضي: 32)

    Returns:
        رمز التحقق
    """
    return secrets.token_hex(length)


# ==============================================
# GENERATE API KEY
# ==============================================


def generate_api_key(
    prefix: str = "moulati",
    length: int = 32,
) -> str:
    """
    توليد مفتاح API.

    Args:
        prefix: بادئة المفتاح
        length: طول المفتاح

    Returns:
        مفتاح API
    """
    token = secrets.token_urlsafe(length)
    return f"{prefix}_{token}"


# ==============================================
# 🔐 JWT TOKENS
# ==============================================


def create_jwt_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    secret_key: Optional[str] = None,
) -> str:
    """
    إنشاء رمز JWT.

    Args:
        data: البيانات المراد تضمينها
        expires_delta: مدة الصلاحية
        secret_key: المفتاح السري (اختياري)

    Returns:
        رمز JWT
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)

    to_encode.update({"exp": expire})

    secret = secret_key or settings.SECRET_KEY

    return jwt.encode(
        to_encode,
        secret,
        algorithm="HS256",
    )


# ==============================================
# DECODE JWT TOKEN
# ==============================================


def decode_jwt_token(
    token: str,
    secret_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    فك تشفير رمز JWT.

    Args:
        token: رمز JWT
        secret_key: المفتاح السري (اختياري)

    Returns:
        البيانات المستخرجة

    Raises:
        jwt.InvalidTokenError: إذا كان الرمز غير صالح
    """
    secret = secret_key or settings.SECRET_KEY

    return jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
    )


# ==============================================
# VERIFY JWT TOKEN
# ==============================================


def verify_jwt_token(
    token: str,
    secret_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    التحقق من صحة رمز JWT.

    Args:
        token: رمز JWT
        secret_key: المفتاح السري (اختياري)

    Returns:
        البيانات المستخرجة أو None إذا كان الرمز غير صالح
    """
    try:
        return decode_jwt_token(token, secret_key)
    except jwt.InvalidTokenError:
        return None


# ==============================================
# 🔑 ENCRYPTION / DECRYPTION
# ==============================================


def encrypt_data(
    data: str,
    key: Optional[str] = None,
) -> str:
    """
    تشفير البيانات (للاستخدام المستقبلي).

    Args:
        data: البيانات النصية
        key: مفتاح التشفير (اختياري)

    Returns:
        البيانات المشفرة
    """
    # TODO: تنفيذ التشفير المتقدم
    # استخدام Fernet أو AES
    return base64.b64encode(data.encode()).decode()


# ==============================================
# DECRYPT DATA
# ==============================================


def decrypt_data(
    encrypted_data: str,
    key: Optional[str] = None,
) -> str:
    """
    فك تشفير البيانات (للاستخدام المستقبلي).

    Args:
        encrypted_data: البيانات المشفرة
        key: مفتاح التشفير (اختياري)

    Returns:
        البيانات النصية
    """
    # TODO: تنفيذ فك التشفير المتقدم
    return base64.b64decode(encrypted_data.encode()).decode()


# ==============================================
# 🛡️ SECURITY HELPERS
# ==============================================


def sanitize_input(
    text: str,
) -> str:
    """
    تنظيف المدخلات من الأحرف الخطرة.

    Args:
        text: النص المراد تنظيفه

    Returns:
        النص المنظف
    """
    # إزالة الأحرف الخطرة
    dangerous_chars = ["<", ">", "&", "'", '"']

    for char in dangerous_chars:
        text = text.replace(char, "")

    return text.strip()


# ==============================================
# VALIDATE PASSWORD STRENGTH
# ==============================================


def validate_password_strength(
    password: str,
) -> Dict[str, Union[bool, str, int]]:
    """
    التحقق من قوة كلمة المرور.

    Args:
        password: كلمة المرور

    Returns:
        قاموس يحتوي على النتيجة والرسالة والدرجة
    """
    result: Dict[str, Union[bool, str, int]] = {
        "valid": True,
        "message": "كلمة المرور قوية",
        "score": 0,
    }

    # التحقق من الطول
    if len(password) < 8:
        result["valid"] = False
        result["message"] = "كلمة المرور يجب أن تكون 8 أحرف على الأقل"
        return result

    # التحقق من الأحرف الكبيرة
    if not any(c.isupper() for c in password):
        result["valid"] = False
        result["message"] = "كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل"
        return result

    # التحقق من الأحرف الصغيرة
    if not any(c.islower() for c in password):
        result["valid"] = False
        result["message"] = "كلمة المرور يجب أن تحتوي على حرف صغير واحد على الأقل"
        return result

    # التحقق من الأرقام
    if not any(c.isdigit() for c in password):
        result["valid"] = False
        result["message"] = "كلمة المرور يجب أن تحتوي على رقم واحد على الأقل"
        return result

    # التحقق من الأحرف الخاصة
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        result["valid"] = False
        result["message"] = "كلمة المرور يجب أن تحتوي على حرف خاص واحد على الأقل"
        return result

    # حساب درجة القوة
    score = 0

    if len(password) >= 12:
        score += 2
    elif len(password) >= 10:
        score += 1

    if any(c.isupper() for c in password) and any(c.islower() for c in password):
        score += 1

    if any(c.isdigit() for c in password):
        score += 1

    if any(c in special_chars for c in password):
        score += 1

    result["score"] = score

    if score >= 5:
        result["message"] = "كلمة المرور قوية جداً"
    elif score >= 3:
        result["message"] = "كلمة المرور قوية"
    else:
        result["message"] = "كلمة المرور ضعيفة"

    return result


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Password
    "hash_password",
    "verify_password",
    "get_password_hash",
    # Tokens
    "generate_session_token",
    "generate_verification_token",
    "generate_api_key",
    # JWT
    "create_jwt_token",
    "decode_jwt_token",
    "verify_jwt_token",
    # Encryption
    "encrypt_data",
    "decrypt_data",
    # Helpers
    "sanitize_input",
    "validate_password_strength",
]
