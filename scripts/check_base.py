# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MAINTENANCE SCRIPT - SCRIPTS / CHECK BASE
# Operational maintenance utility for the MoulAI platform.
# ==============================================

"""Operational maintenance script for check base.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# scripts/check_base.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 50)
print("🔍 التحقق من Base في النماذج")
print("=" * 50)

# استيراد Base من database
from app.core.database import Base

print(f"Base من database: {id(Base)}")

# استيراد Owner والتحقق من Base الخاص به
from app.models.owner import Owner

print(f"Base في Owner: {id(Owner.__bases__[0])}")
print(f"هل Base متطابق؟ {Base is Owner.__bases__[0]}")

# استيراد Restaurant والتحقق
from app.models.restaurant import Restaurant

print(f"Base في Restaurant: {id(Restaurant.__bases__[0])}")
print(f"هل Base متطابق؟ {Base is Restaurant.__bases__[0]}")

# استيراد جميع النماذج
print("\n📋 استيراد جميع النماذج...")
import app.models  # noqa: F401  # Register ORM models in Base.metadata.

print(f"\n📊 عدد الجداول في Base.metadata: {len(Base.metadata.tables)}")
for table in Base.metadata.tables.values():
    print(f"   - {table.name}")
