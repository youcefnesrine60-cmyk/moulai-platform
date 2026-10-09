# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MAINTENANCE SCRIPT - SCRIPTS / CHECK MODELS
# Operational maintenance utility for the MoulAI platform.
# ==============================================

"""Operational maintenance script for check models.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# scripts/check_models.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base

# ✅ استيراد جميع النماذج
import app.models  # noqa: F401  # Register ORM models in Base.metadata.

print("=" * 50)
print("📋 النماذج المسجلة في Base.metadata:")
print("=" * 50)

for table in Base.metadata.tables.values():
    print(f"   - {table.name}")

print("=" * 50)
print(f"إجمالي عدد الجداول: {len(Base.metadata.tables)}")
