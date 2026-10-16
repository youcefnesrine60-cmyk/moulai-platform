# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Explicit provider contracts; only manual postal transfers are implemented."""

# ==============================================
# IMPORTS
# ==============================================

from .registry import get_payment_provider

# ==============================================
# EXPORTS
# ==============================================

__all__ = ["get_payment_provider"]
