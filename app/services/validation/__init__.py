# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PACKAGE INITIALIZER - APP / SERVICES / VALIDATION /   INIT
# Package initialization and public exports component.
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ============================================
# ✅ VALIDATION SERVICE EXPORTS
# ============================================

from app.services.validation.sanitizer import (
    sanitize_restaurant,
    sanitize_owner,
    sanitize_wilaya,
    sanitize_description,
)

from app.services.validation.phone_validator import validate_phone, normalize_phone

__all__ = [
    # Sanitizers
    "sanitize_restaurant",
    "sanitize_owner",
    "sanitize_wilaya",
    "sanitize_description",
    # Phone Validators
    "validate_phone",
    "normalize_phone",
]
