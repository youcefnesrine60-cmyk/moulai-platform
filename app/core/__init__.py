# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🚀 CORE MODULE
# المكونات الأساسية للمشروع
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ==============================================
# 📦 EXCEPTIONS
# ==============================================

from app.core.exceptions import (
    # Base
    AppException,
    # Not Found
    NotFoundError,
    RestaurantNotFoundError,
    AdminNotFoundError,
    BranchNotFoundError,
    ProductNotFoundError,
    OrderNotFoundError,
    UserNotFoundError,
    # Conflict
    ConflictError,
    DuplicateUsernameError,
    DuplicateEmailError,
    DuplicateChatIdError,
    # Unauthorized
    UnauthorizedError,
    InvalidCredentialsError,
    InvalidSessionError,
    InsufficientPermissionError,
    AccountInactiveError,
    # Validation
    ValidationError,
    InvalidInputError,
    MissingRequiredFieldError,
    # Forbidden
    ForbiddenError,
    RestaurantAccessDeniedError,
    # Payment
    PaymentError,
    InsufficientBalanceError,
    # Database
    DatabaseError,
    DuplicateEntryError,
    # Telegram
    TelegramAPIError,
    TelegramSendMessageError,
    # Rate Limit
    RateLimitError,
    # Subscription
    SubscriptionError,
    SubscriptionExpiredError,
    # Branch
    BranchLimitExceededError,
)

# ==============================================
# 🔐 SECURITY
# ==============================================

from app.core.security import (
    # Password
    hash_password,
    verify_password,
    get_password_hash,
    # Tokens
    generate_session_token,
    generate_verification_token,
    generate_api_key,
    # JWT
    create_jwt_token,
    decode_jwt_token,
    verify_jwt_token,
    # Encryption
    encrypt_data,
    decrypt_data,
    # Helpers
    sanitize_input,
    validate_password_strength,
)

# ==============================================
# 📊 DATABASE
# ==============================================

from app.core.database import (
    Base,
    get_db,
    get_async_session,
    get_session,
    init_db,
    drop_db,
    close_db,
    check_db_connection,
    AsyncSessionLocal,
)

# ==============================================
# 🤖 AI CLIENT
# ==============================================

from app.core.ai_client import AIClient, ai_client, AIMessage, AIMessages, AIResponse

# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Exceptions
    "AppException",
    "NotFoundError",
    "RestaurantNotFoundError",
    "AdminNotFoundError",
    "BranchNotFoundError",
    "ProductNotFoundError",
    "OrderNotFoundError",
    "UserNotFoundError",
    "ConflictError",
    "DuplicateUsernameError",
    "DuplicateEmailError",
    "DuplicateChatIdError",
    "UnauthorizedError",
    "InvalidCredentialsError",
    "InvalidSessionError",
    "InsufficientPermissionError",
    "AccountInactiveError",
    "ValidationError",
    "InvalidInputError",
    "MissingRequiredFieldError",
    "ForbiddenError",
    "RestaurantAccessDeniedError",
    "PaymentError",
    "InsufficientBalanceError",
    "DatabaseError",
    "DuplicateEntryError",
    "TelegramAPIError",
    "TelegramSendMessageError",
    "RateLimitError",
    "SubscriptionError",
    "SubscriptionExpiredError",
    "BranchLimitExceededError",
    # Security
    "hash_password",
    "verify_password",
    "get_password_hash",
    "generate_session_token",
    "generate_verification_token",
    "generate_api_key",
    "create_jwt_token",
    "decode_jwt_token",
    "verify_jwt_token",
    "encrypt_data",
    "decrypt_data",
    "sanitize_input",
    "validate_password_strength",
    # Database
    "Base",
    "get_db",
    "get_async_session",
    "get_session",
    "init_db",
    "drop_db",
    "close_db",
    "check_db_connection",
    "AsyncSessionLocal",
    # AI CLIENT
    "AIClient",
    "ai_client",
    "AIMessage",
    "AIMessages",
    "AIResponse",
]
